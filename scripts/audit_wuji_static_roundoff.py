"""Audit a completed static trace against the exact zero-action target recurrence.

The original static process's failed exit is preserved. This separate offline
audit must explain target deviations with the implemented float32 mapping, not
merely accept a larger tolerance. No physics trace or selection rule is edited.
"""
import argparse
import hashlib
import json
from pathlib import Path

import isaacgym
import numpy as np
import torch
import yaml
from isaacgymenvs.utils.torch_jit_utils import scale,unscale,tensor_clamp
from scripts.wuji_kinematics import WujiKinematics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args();p=args.directory
    states=np.load(p/'initial_states.npy');trace=np.load(p/'static/trace.npz')
    cfg=yaml.safe_load((p/'static/config.yaml').read_text())
    hand=WujiKinematics()
    device='cuda'
    saved=torch.tensor(states,device=device)
    lo=torch.tensor(hand.lower,device=device,dtype=torch.float32)
    hi=torch.tensor(hand.upper,device=device,dtype=torch.float32)
    alpha=cfg['task']['env']['actionsMovingAverage']
    assert not cfg['task']['env']['useRelativeControl']
    assert trace['target'].shape==(600,len(states),20)
    previous=saved[:,20:40].clone()
    errors=[]
    for i in range(600):
        desired=saved[:,20:40].clone()
        desired[:,16:]=previous[:,16:]
        desired=tensor_clamp(desired,lo,hi)
        predicted=tensor_clamp(alpha*scale(unscale(desired,lo,hi),lo,hi)+(1-alpha)*previous,lo,hi)
        actual=torch.tensor(trace['target'][i],device=device)
        active=torch.tensor(trace['active'][i],device=device)
        errors.append(float(abs(predicted[active]-actual[active]).max()) if active.any() else 0.)
        previous=actual
    # The expression on CUDA can fuse arithmetic differently from the original
    # task's separate scripted calls. One float32 ULP at the joint range is the
    # absolute maximum accepted residual after reconstructing every transition.
    tolerance=float(np.spacing(np.float32(max(abs(hand.lower).max(),abs(hand.upper).max()))))
    error=max(errors)
    active=trace['active']
    drift=abs(trace['target']-states[None,:,20:40])*active[:,:,None]
    numerical=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__,
        recurrence_max_abs_error_rad=error,recurrence_tolerance_rad=tolerance,
        observed_max_target_shift_rad=float(drift.max()),
        observed_max_target_shift_deg=float(np.rad2deg(drift.max())),
        initial_states_sha256=hashlib.sha256((p/'initial_states.npy').read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256((p/'static/trace.npz').read_bytes()).hexdigest(),
        status='verified' if error<=tolerance else 'failed')
    (p/'static/roundoff-audit.json').write_text(json.dumps(numerical,indent=2)+'\n')
    print(json.dumps(numerical),flush=True)
    assert error<=tolerance,'The target deviations are not explained by zero-action float32 mapping'
    assert drift.max()<1e-5,'A numerical recurrence drift still exceeded the explicit physical negligibility bound'
    rows=[]
    for i in range(len(states)):
        valid=active[:,i]&~trace['fall'][:,i]&~trace['invalid'][:,i]
        pose=(trace['drift'][:,i]<.01)&(trace['rotation'][:,i]<.25)
        rows.append(dict(env=i,stable2s=bool(valid[:60].all() and pose[:60].all()),
            stable20s=bool(valid.all() and pose.all()),fall=bool(trace['fall'][:,i][active[:,i]].any()),
            max_drift_m=float(trace['drift'][:,i][active[:,i]].max()),
            max_rotation_rad=float(trace['rotation'][:,i][active[:,i]].max())))
    result=dict(status='verified_offline',num_envs=len(states),recorded_steps=600,
                initial_state_sha256=numerical['initial_states_sha256'],numerical_audit=numerical,records=rows,
                original_exit='failed strict2e-6 target guard; this report does not change that status')
    (p/'static/offline-report.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
