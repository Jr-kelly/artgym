"""Collect teacher-history/state pairs for a bounded optimization diagnostic.

This dataset is development-only. It never supplies a deployed actor with live
truth. Fixed train/validation environment rows are chosen before collection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.wuji_physical_state_encoder import history_input, encode_target, SCALES

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    original=wuji_goal_common.make_player
    refs={}
    rows=[]
    selected=np.array([i+j for i in [0,100,200] for j in range(30)])
    checks=dict(latest_history_matches=0,actual_actions=0)
    def make_player(cfg,path):
        OmegaConf.update(cfg,'task.env.enableStudentEncoderObs',True,force_add=True)
        env,player=original(cfg,path)
        (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
        assert env.student_encoder_obs_enabled and env.joint_noise==0
        model=player.model.eval()
        refs.update(model=model,digest=tensor_digest(model.state_dict()))
        action=player.get_action
        pre=env.pre_physics_step
        expected={}
        index=torch.tensor(selected,device=player.device)
        ticks=[0]
        def pre_step(a):
            pre(a)
            assert torch.equal(env.actions,expected['action'])
            checks['actual_actions']+=env.num_envs
        env.pre_physics_step=pre_step
        def capture(obs,is_deterministic=False,**kwargs):
            assert is_deterministic
            assert torch.equal(env.proprioception_buf[:,-1],obs[:,55:95])
            checks['latest_history_matches']+=env.num_envs
            if ticks[0]%4==0:
                history=history_input(env.proprioception_buf,obs)
                target=encode_target(obs[:,:55],obs[:,111:132])*obs.new_tensor(SCALES)
                rows.append(dict(history=history[index].cpu().numpy().copy(),target=target[index].cpu().numpy().copy(),
                                 active=env.eval_active_mask[index].cpu().numpy().copy(),step=ticks[0]))
            result=action(obs,is_deterministic=True,**kwargs)
            expected['action']=result.clone()
            ticks[0]+=1
            return result
        player.get_action=capture
        return env,player
    wuji_goal_common.make_player=make_player
    argv=sys.argv
    try:
        sys.argv=[argv[0],'--checkpoint',str(ROOT/TEACHER),'--output',str(args.output),
                  '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
                  '--object','knife_wuji_bridge3_20260922','--initial-states',
                  str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
                  '--stage-seconds','2','--seed','20261060']
        from scripts.audit_wuji_timed_commands import main as audit
        audit()
    finally:
        sys.argv=argv
        wuji_goal_common.make_player=original
    assert tensor_digest(refs['model'].state_dict())==refs['digest']
    report=json.loads((args.output/'report.json').read_text())
    assert report['recorded_steps']==600 and len(rows)==150
    assert checks['actual_actions']==checks['latest_history_matches']==600*332
    arrays={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    arrays['initial_rows']=selected
    arrays['train_rows']=(selected%100)<20
    dataset=args.output/'history-state-pairs.npz'
    np.savez_compressed(dataset,**arrays)
    manifest=dict(status='passed',checks=checks,source_teacher_sha256=hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),initial_rows=selected.tolist(),
        split='Each training grasp perturbation rows0:20 training,20:30validation; every4thframe ofone20s teacher trajectory. Reused development states, no independent generalization.',
        label='physical displacement3/worldrotationvector3/sliderdisplacement/velocity; SI units',
        teacher_unchanged=True,teacher_tensor_sha256=refs['digest'],joint_success=report['stable_full_all_endpoints'],
        scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))


if __name__=='__main__':
    main()
