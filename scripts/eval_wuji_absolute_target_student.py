"""Frozen joint-command student in real physics, without teacher actions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_absolute_target_student import TargetStudent, features, action_from_prediction
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import atomic_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=int,choices=[2,5],required=True)
    p.add_argument('--runtime-check',action='store_true')
    args=p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    sha=hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    assert sha==json.loads(args.artifact.with_suffix('.json').read_text())['sha256']
    artifact=torch.load(args.artifact,map_location='cpu')
    assert hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest()==artifact['provenance']['teacher_sha256']
    original=wuji_goal_common.make_player
    refs={}; rows=[]
    checks=dict(teacher_action_calls=0,physics_transitions=0,privileged_invariance=0,
                actual_target_max_error=0.,slew_limited_components=0)
    def make_player(cfg,checkpoint):
        env,player=original(cfg,checkpoint)
        network=TargetStudent(artifact['feature_mean'],artifact['feature_scale']).to(player.device).eval()
        network.load_state_dict(artifact['state_dict'])
        refs.update(network=network,before=tensor_digest(network.state_dict()))
        for param in network.parameters():
            param.requires_grad_(False)
        expected={}
        # This detects an accidental call to the teacher policy, rather than
        # inferring absence from a declared policy name.
        def forbid_teacher(module,inputs):
            checks['teacher_action_calls']+=1
            raise AssertionError('Teacher policy was called during student evaluation')
        refs['guard']=player.model.register_forward_pre_hook(forbid_teacher)
        original_pre=env.pre_physics_step
        def pre(action):
            original_pre(action)
            assert torch.equal(env.actions,expected['action'])
            err=float((env.cur_targets[:,:20]-expected['applied_target']).abs().max())
            assert err<1e-6,err
            checks['actual_target_max_error']=max(checks['actual_target_max_error'],err)
            checks['physics_transitions']+=env.num_envs
        env.pre_physics_step=pre
        def action(obs,is_deterministic=False,**kwargs):
            assert is_deterministic
            initial=env.init_targets[:,:20]
            current=env.cur_targets[:,:20]
            lower,upper=env.hand_dof_lower_limits,env.hand_dof_upper_limits
            with torch.no_grad():
                x=features(obs,initial,lower,upper)
                prediction=network(x)
                result,desired=action_from_prediction(prediction,initial,current,lower,upper,artifact['arm'])
                assert torch.isfinite(result).all() and result.shape==(env.num_envs,20)
                applied=initial+.04*result
                applied[:,16:]=current[:,16:]+.025*result[:,16:]
                applied=torch.maximum(torch.minimum(applied,upper),lower)
                checks['slew_limited_components']+=int(((applied-desired).abs()>1e-6).sum())
                if args.runtime_check or not rows:
                    changed=obs.clone();changed[:,111:137]+=13.
                    otherx=features(changed,initial,lower,upper)
                    assert torch.equal(x,otherx)
                    other,_=action_from_prediction(network(otherx),initial,current,lower,upper,artifact['arm'])
                    assert torch.equal(result,other)
                    checks['privileged_invariance']+=env.num_envs
                expected.update(action=result.clone(),applied_target=applied.clone())
                rows.append(dict(prediction=prediction.cpu().numpy(),desired=desired.cpu().numpy(),
                    incoming=current.cpu().numpy().copy(),active=env.eval_active_mask.cpu().numpy().copy()))
                if args.runtime_check:
                    rows[-1]['features']=x.cpu().numpy()
            return result
        player.get_action=action
        return env,player
    wuji_goal_common.make_player=make_player
    argv=sys.argv
    try:
        sys.argv=[argv[0],'--checkpoint',str(ROOT/TEACHER),'--output',str(args.output),
            '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_bridge3_20260922','--initial-states',
            str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
            '--stage-seconds',str(args.seconds),'--seed','20261060']
        if args.runtime_check:
            sys.argv+=['--initial-state-rows','0','100','200']
        from scripts.audit_wuji_timed_commands import main as evaluate
        evaluate()
    finally:
        sys.argv=argv;wuji_goal_common.make_player=original
        if 'guard' in refs:
            refs['guard'].remove()
    assert tensor_digest(refs['network'].state_dict())==refs['before']
    report=json.loads((args.output/'report.json').read_text())
    assert checks['physics_transitions']==report['num_envs']*report['recorded_steps']
    assert checks['teacher_action_calls']==0
    (args.output/'environment-setup-report.json').write_text(json.dumps(report,indent=2)+'\n')
    report.update(policy_kind='learned_joint_command_student',command_representation=artifact['arm'],
        environment_setup_checkpoint_sha256=report['checkpoint_sha256'],checkpoint_sha256=sha,
        student_sha256=sha,current_object_actor_input=False,teacher_actions=0,
        scope='Frozen116-input MLP from teacher demonstrations; same physical control limits. Reused development initial states, not independent validation.')
    atomic_json(args.output/'report.json',report)
    np.savez_compressed(args.output/'command-predictions.npz',**{k:np.stack([r[k] for r in rows]) for k in rows[0]})
    audit=dict(status='passed',checks=checks,model_unchanged=True,artifact_sha256=sha,
        arm=artifact['arm'],update=artifact['update'],current_object_input=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__)
    atomic_json(args.output/'command-student-audit.json',audit)
    print(json.dumps(audit))


if __name__=='__main__':
    main()
