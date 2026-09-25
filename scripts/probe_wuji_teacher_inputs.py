"""Frozen-teacher input interventions with coherent knife kinematics.

This is a privileged diagnostic, never a deployable student. Only the actor
encoder's normalized21 inputs change. Critic inputs, physics and scorer stay
unchanged. Removing a field can be out of training distribution; failure is
evidence about this frozen controller, not an impossibility proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from scripts import wuji_goal_common
import numpy as np
import torch
from isaacgymenvs.utils.torch_jit_utils import quat_apply
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER

ROOT=Path(__file__).resolve().parents[1]
MODES=('full','body_initial','slider_initial','state_initial','properties_default')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=MODES,required=True)
    p.add_argument('--seconds',type=int,choices=[2,5],required=True)
    p.add_argument('--runtime-check',action='store_true')
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    checkpoint=ROOT/TEACHER
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    original_make=wuji_goal_common.make_player
    rows=[];refs={}
    checks=dict(actual_actions=0,actor_input_checks=0,same_state_reference=0,
        true_kinematic_position_max_m=0.,true_kinematic_quaternion_max=0.,
        reference_actor_rnn_max=0.,reference_action_max=0.)

    def make_player(cfg,path):
        env,player=original_make(cfg,path);model=player.model.eval()
        refs.update(model=model,digest=tensor_digest(model.state_dict()))
        assert model.a2c_network.policy_obs_dim==111 and model.a2c_network.privileged_obs_dim==21
        assert env.object_mass.shape==(env.num_envs,2)
        urdf=ROOT/cfg.object.asset.asset_root/'000/mobility.urdf'
        joint=ET.parse(urdf).getroot().find('joint')
        assert joint.attrib['type']=='prismatic' and joint.find('axis').attrib['xyz']=='0 0 1'
        origin=[float(v) for v in joint.find('origin').attrib['xyz'].split()]
        assert origin[0]==0 and joint.find('origin').attrib.get('rpy','0 0 0')=='0 0 0'
        # The already-declared acquisition frame maps original[x,y,z] to[x,-z,y].
        def slider_pose(body,delta):
            offset=torch.zeros((env.num_envs,3),device=player.device)
            offset[:,1]=-(origin[2]+env.init_obj_dof_pos[:,0]+delta)
            offset[:,2]=origin[1]
            return torch.cat([body[:,:3]+quat_apply(body[:,3:7],offset),body[:,3:7]],-1)

        original_action=player.get_action;pre_physics=env.pre_physics_step
        expected={};enabled=[True]
        def hook(module,inputs):
            if not enabled[0]:return None
            assert torch.equal(inputs[0],expected['true_normalized'])
            checks['actor_input_checks']+=env.num_envs
            return (expected['modified_normalized'],)
        handle=model.a2c_network.priv_encoder.register_forward_pre_hook(hook)
        refs['hook']=handle
        def pre_step(action):
            pre_physics(action)
            assert torch.equal(env.actions,expected['action'])
            checks['actual_actions']+=env.num_envs
        env.pre_physics_step=pre_step

        def observed(obs,is_deterministic=False,**kwargs):
            assert is_deterministic and obs.shape==(env.num_envs,138)
            true=obs[:,111:132].detach().clone();modified=true.clone()
            initial_body=obs[:,20:27]
            assert torch.isfinite(true).all() and torch.isfinite(initial_body).all()
            calculated=slider_pose(true[:,:7],true[:,19])
            error=(calculated[:,:3]-true[:,7:10]).abs().amax(-1)
            quat_error=torch.minimum((calculated[:,3:]-true[:,10:14]).abs().amax(-1),
                                     (calculated[:,3:]+true[:,10:14]).abs().amax(-1))
            active=env.eval_active_mask
            if active.any():
                checks['true_kinematic_position_max_m']=max(checks['true_kinematic_position_max_m'],float(error[active].max()))
                checks['true_kinematic_quaternion_max']=max(checks['true_kinematic_quaternion_max'],float(quat_error[active].max()))
            if args.mode in ('body_initial','state_initial'):
                modified[:,:7]=initial_body
            if args.mode in ('slider_initial','state_initial'):
                modified[:,19:21]=0
            if args.mode in ('body_initial','slider_initial','state_initial'):
                modified[:,7:14]=slider_pose(modified[:,:7],modified[:,19])
            if args.mode=='properties_default':
                defaults=env.object_cfg['default_props']
                modified[:,14:19]=modified.new_tensor(list(defaults['mass'])+[
                    float(defaults['friction']),float(defaults['dof_damping']),float(defaults.get('dof_stiffness',0.))])
            changed_obs=obs.clone();changed_obs[:,111:132]=modified
            with torch.no_grad():
                expected['true_normalized']=model.norm_obs(player._preproc_obs(obs))[:,111:132]
                expected['modified_normalized']=model.norm_obs(player._preproc_obs(changed_obs))[:,111:132]
                assert torch.equal(obs[:,:111],changed_obs[:,:111])
                assert torch.equal(obs[:,132:],changed_obs[:,132:])
                if args.mode=='full':assert torch.equal(obs,changed_obs)
                incoming=[v.clone() for v in player.states]
                action=original_action(obs,is_deterministic=True,**kwargs)
                outgoing=[v.clone() for v in player.states]
                if args.runtime_check:
                    # Independent reference applies the intervention before
                    # normalization; critic state may differ, actor may not.
                    with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
                        enabled[0]=False;player.states=[v.clone() for v in incoming]
                        try:reference=original_action(changed_obs,is_deterministic=True,**kwargs)
                        finally:enabled[0]=True
                        action_error=float((reference-action).abs().max())
                        rnn_error=max(float((a-b).abs().max()) for a,b in zip(player.states[:2],outgoing[:2]))
                        checks['reference_action_max']=max(checks['reference_action_max'],action_error)
                        checks['reference_actor_rnn_max']=max(checks['reference_actor_rnn_max'],rnn_error)
                        assert action_error==0 and rnn_error==0
                        if args.mode=='full':assert all(torch.equal(a,b) for a,b in zip(player.states,outgoing))
                        player.states=outgoing
                        checks['same_state_reference']+=env.num_envs
            expected['action']=action.detach().clone()
            row=dict(true_privileged=true,actor_privileged=modified,active=active,
                goal=env.goal_obj_dof_pos[:,0],slider=env.obj_dof_pos[:,0],action=action)
            rows.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})
            return action

        player.get_action=observed
        return env,player

    wuji_goal_common.make_player=make_player;oldargv=sys.argv
    try:
        sys.argv=[oldargv[0],'--checkpoint',str(checkpoint),'--output',str(args.output),
            '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_bridge3_20260922','--initial-states',
            str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
            '--stage-seconds',str(args.seconds),'--seed','20261060']
        if args.runtime_check:sys.argv+=['--initial-state-rows','0','100','200']
        from scripts.audit_wuji_timed_commands import main as audit
        audit()
    finally:
        sys.argv=oldargv;wuji_goal_common.make_player=original_make
        if 'hook' in refs:refs['hook'].remove()
    assert tensor_digest(refs['model'].state_dict())==refs['digest']
    original_report=json.loads((args.output/'report.json').read_text())
    actual_steps=original_report['recorded_steps']
    count=(3 if args.runtime_check else 332)*actual_steps
    assert 0<actual_steps<=600 and len(rows)==actual_steps
    assert checks['actual_actions']==checks['actor_input_checks']==count
    if actual_steps<600:
        # The unchanged evaluator ends when every environment is terminal.
        # Preserve this failed population; do not invent unexecuted transitions.
        assert original_report['alive_full']==0
        assert all(r['fall'] or r['invalid'] for r in original_report['records'])
    if args.runtime_check:assert checks['same_state_reference']==count
    # Check kinematic identity on actual physics, including all active failures.
    assert checks['true_kinematic_position_max_m']<5e-5,checks
    assert checks['true_kinematic_quaternion_max']<5e-4,checks
    np.savez_compressed(args.output/'input-trace.npz',**{k:np.stack([x[k] for x in rows]) for k in rows[0]})
    result=dict(status='passed',mode=args.mode,runtime=args.runtime_check,checks=checks,
        recorded_steps=actual_steps,maximum_steps=600,actual_physics_transitions=count,
        early_population_termination=actual_steps<600,
        weights_unchanged=True,model_tensor_sha256=refs['digest'],teacher_checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'input-probe-report.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.output/'input-probe-source.py').write_bytes(Path(__file__).read_bytes())
    report_path=args.output/'report.json';report=json.loads(report_path.read_text())
    report.update(policy_kind='privileged_teacher_input_intervention',input_intervention=result)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
