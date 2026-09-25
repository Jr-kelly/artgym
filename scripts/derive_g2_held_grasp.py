"""Derive a motor-planning start from an executed lift, never a reset state."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.g2_seating_feedback import ContactCorrection
from scripts.wuji_kinematics import FINGERS


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--phase',default='lift',help='Executed phase end to use as motor-planning reference; never a simulator reset.')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.trial/'grasp-plan.json').read_text());t=np.load(a.trial/'trace.npz')
    selected=np.flatnonzero(t['phase']==a.phase)
    if not len(selected):raise ValueError('Phase absent in executed trace: '+a.phase)
    i=int(selected[-1]);physics=json.loads((a.trial/'physics.json').read_text())
    wrist=transform(t['wrist'][i,:3],t['wrist'][i,3:]);obj=transform(t['object'][i,:3],t['object'][i,3:])
    relative=np.linalg.inv(obj)@wrist
    pairs=[json.loads(l) for l in (a.trial/'knife-contact-pairs.jsonl').read_text().splitlines()]
    normals=[]
    for f in FINGERS:
        rows=[v for v in pairs if i-4<=v['step']<=i and (f in v['body1'] or f in v['body0'])]
        if not rows:raise ValueError('No measured knife contact for '+f)
        normal=sum(np.array(v['normal'])*(-1 if f in v['body1'] else 1)@
                   Rotation.from_quat(t['object'][v['step'],3:]).as_matrix()*v['lambda_value'] for v in rows)
        normal[2]=0;normal/=np.linalg.norm(normal);normals.append(normal)
    points,_,_=ContactCorrection().contacts(t['q'][i],relative,normals)
    data.update(wrist_in_knife=relative.tolist(),touch_q=t['q'][i].tolist(),
        close_q=t['targets'][i,physics['hand_indices']].tolist(),contact_targets=points.tolist(),
        contact_normals=np.asarray(normals).tolist(),source_trial=str(a.trial),source_step=i,
        source_trace_sha256=hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),source_phase=a.phase,
        validation='Actual executed phase-end geometry for motor planning only. Original tabletop grasp plan remains unchanged; never load as simulator state.')
    a.output.write_text(json.dumps(data,indent=2)+'\n');print(str(a.output))

if __name__=='__main__':main()
