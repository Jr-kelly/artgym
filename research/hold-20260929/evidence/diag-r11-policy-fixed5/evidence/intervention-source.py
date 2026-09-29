"""Mechanistic intervention, NOT a learned-policy success or deployment result.

Once the observed slider is within2mm for9 consecutive transitions in a command,
set subsequent thumb increments to zero until the externally scheduled next
command. Nonthumb actions remain policy generated. This freezes the commanded
thumb target, not measured joint position or contact force. The paired policy
mode runs the identical wrapper without the intervention.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from scripts import audit_wuji_multigrasp as audit
import numpy as np
import torch


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--intervention',choices=['policy','thumb_latch'],required=True)
    args,remaining=parser.parse_known_args()
    sys.argv=[sys.argv[0]]+remaining
    output=Path(remaining[remaining.index('--output')+1])
    original=audit.make_player;frames=[]
    def make_player(*values,**kwargs):
        env,player=original(*values,**kwargs);policy=player.get_action
        goal=None;streak=torch.zeros(env.num_envs,device=env.device,dtype=torch.long)
        latched=torch.zeros(env.num_envs,device=env.device,dtype=torch.bool)
        calls=0
        def action(*values,**kwargs):
            nonlocal goal,calls
            result=policy(*values,**kwargs)
            current=env.goal_obj_dof_pos[:,0].clone()
            changed=torch.ones_like(latched) if goal is None else current!=goal
            streak[changed]=0;latched[changed]=False
            if calls:
                valid=(env.eval_active_mask & ~env.debug_reset_cause_fall & ~env.debug_reset_cause_invalid)
                within=(torch.abs(env.obj_dof_pos[:,0]-current)<.002)&valid&~changed
                streak[~within]=0;streak[within]+=1
                latched[:] |= streak>=9
            commanded=result.clone()
            if args.intervention=='thumb_latch':commanded[latched,16:20]=0
            frames.append(dict(latched=latched.detach().cpu().numpy().copy(),
                raw_action=result.detach().cpu().numpy().copy(),sent_action=commanded.detach().cpu().numpy().copy()))
            goal=current;calls+=1
            return commanded
        player.get_action=action
        return env,player
    audit.make_player=make_player
    audit.main()
    source=Path(__file__);(output/'intervention-source.py').write_bytes(source.read_bytes())
    np.savez_compressed(output/'intervention.npz',**{key:np.stack([row[key] for row in frames]) for key in frames[0]})
    report=json.loads((output/'report.json').read_text())
    report.update(control_mode='scripted_thumb_target_latch' if args.intervention=='thumb_latch' else 'privileged_teacher',
        intervention=dict(mode=args.intervention,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope=__doc__,
                          action_calls=len(frames),latched_steps=int(sum(row['latched'].sum() for row in frames))))
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
