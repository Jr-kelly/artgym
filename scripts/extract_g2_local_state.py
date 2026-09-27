"""Extract one actually executed continuous state and its real50-frame history.

No simulation, interpolation, filtering or modification of the measured state.
Its later use is explicitly a local diagnostic reset, not continuous success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--frame',type=int,default=-1)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert not a.output.exists()
    t=np.load(a.trace)
    i=a.frame if a.frame>=0 else len(t['time'])+a.frame
    assert 49<=i<len(t['time'])
    keys=['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state',
          'reference_targets','targets','arm_integral_state','wrist','object','slider_pose','q','slider']
    state={k:t[k][i].copy() for k in keys}
    state.update(history_q=t['q'][i-49:i+1].copy(),history_action=t['action'][i-49:i+1].copy(),
                 frame=np.array(i),source_time=t['time'][i].copy())
    np.savez_compressed(a.output,**state)
    provenance=dict(scope='measured continuous state; later local reset cannot count as acquisition',
        source_trace=str(a.trace.resolve()),source_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),
        frame=i,source_time=float(t['time'][i]),phase=str(t['phase'][i]),
        actual_history_frames=50,state_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
        contact_cache='PhysX hidden contact cache unavailable; first-step and continuous checks required')
    a.output.with_suffix('.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(provenance))


if __name__=='__main__':main()
