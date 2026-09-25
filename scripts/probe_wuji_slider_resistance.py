"""Common-state diagnostic of teacher behavior at increasing slider damping.

The five conditions reuse the same first 20 development perturbations. Only
slider damping changes. This is a simulator sensitivity probe, not calibrated
real slider resistance or unseen-object generalization. Privileged damping
observations match the actual properties; policy actions remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common
import numpy as np
import torch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--initial-states',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).read_bytes();(args.output/'resistance_probe_source.py').write_bytes(source)
    states=np.load(args.initial_states)[:20]
    matrix=np.tile(states,(5,1));np.save(args.output/'common_states.npy',matrix)
    damping=np.repeat([.3,3.,30.,100.,300.],20)
    original_make=wuji_goal_common.make_player
    checks=dict(observation_refreshes=0,actual_damping=[])

    def make_player(cfg,checkpoint):
        env,player=original_make(cfg,checkpoint)
        assert not env.randomize
        for i,value in enumerate(damping):
            props=env.gym.get_actor_dof_properties(env.envs[i],env.object_handles[i])
            props['damping'][:]=value
            env.gym.set_actor_dof_properties(env.envs[i],env.object_handles[i],props)
            actual=env.gym.get_actor_dof_properties(env.envs[i],env.object_handles[i])['damping'][0]
            assert np.isclose(actual,value)
            checks['actual_damping'].append(float(actual))
        base_refresh=env._get_object_props

        def refresh():
            base_refresh()
            env.object_dof_damping[:,0]=torch.as_tensor(damping,device=env.device,dtype=env.object_dof_damping.dtype)
            checks['observation_refreshes']+=1

        env._get_object_props=refresh;refresh()
        original_action=player.get_action

        def action(*a,**kw):
            assert torch.allclose(env.object_dof_damping[:,0],torch.as_tensor(damping,device=env.device,dtype=torch.float32))
            return original_action(*a,**kw)

        player.get_action=action
        return env,player

    wuji_goal_common.make_player=make_player
    from scripts import audit_wuji_timed_commands
    previous=sys.argv
    try:
        sys.argv=[previous[0],'--checkpoint',str(args.checkpoint),'--initial-states',str(args.output/'common_states.npy'),
            '--task','wuji_acquisition_official_support40mrad','--hand','wuji_paper_official_actuator',
            '--stage-seconds','2','--seed','1616','--output',str(args.output)]
        audit_wuji_timed_commands.main()
    finally:sys.argv=previous;wuji_goal_common.make_player=original_make
    report=json.loads((args.output/'report.json').read_text())
    results=[]
    for i,value in enumerate([.3,3.,30.,100.,300.]):
        records=report['records'][i*20:(i+1)*20]
        results.append(dict(damping_Ns_per_m=value,viscous_force_at_20mm_per_s_N=value*.02,
            trials=20,**{k:sum(row[k] for row in records) for k in ['first_cycle','first_cycle_strict',
            'all_commands_attained','all_endpoints_held','stable_full','stable_full_all_endpoints','fall']}))
    result=dict(status='completed',results=results,physics_checks=checks,scope=__doc__,
                source_sha256=hashlib.sha256(source).hexdigest(),checkpoint_sha256=report['checkpoint_sha256'],
                initial_source_sha256=hashlib.sha256(args.initial_states.read_bytes()).hexdigest(),
                rows_per_condition=list(range(20)),configuration_note='config.yaml contains base settings; actual per-environment damping overrides and privileged observations are recorded here.')
    (args.output/'resistance_report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
