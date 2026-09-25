"""Summarize actual G2 trajectories and keep failed development trials visible."""
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
from scipy.spatial.transform import Rotation


def audit(path):
    trace=np.load(path/'trace.npz');report=json.loads((path/'report.json').read_text())
    physics=json.loads((path/'physics.json').read_text()) if (path/'physics.json').exists() else None
    arm=trace['arm_q'];out=dict(name=path.name,frames=len(arm),group=report['group'],
        grasp_success=report.get('grasp_success'),basic_10mm=report.get('basic_10mm'),
        strict_2mm=report.get('strict_2mm'),whole_success=report.get('whole_success'),
        stable_world_10mm_025rad=report.get('stable_world_10mm_025rad'),
        failure_class=report.get('failure_class'),operation_steps=report.get('operation_steps'))
    if arm.shape[1]==7:
        k=G2Kinematics();poses=np.array([k.forward(q) for q in arm]);measured=trace['wrist']
        out.update(arm_limit_violation_rad=float(np.maximum(np.maximum(k.lower-arm,arm-k.upper),0).max()),
            fk_position_error_max_m=float(np.linalg.norm(poses[:,:3,3]-measured[:,:3],axis=1).max()),
            fk_rotation_error_max_rad=float((Rotation.from_matrix(poses[:,:3,:3]).inv()*Rotation.from_quat(measured[:,3:])).magnitude().max()))
        if physics:
            idx=physics['arm_indices'];targets=trace['targets'][:,idx];dt=float(np.median(np.diff(trace['time'])))
            out['command_velocity_max_rad_s']=(np.abs(np.diff(targets,axis=0))/dt).max(0).tolist()
            out['arm_velocity_limits_rad_s']=k.velocity.tolist()
            out['command_velocity_violation_max_rad_s']=float(np.maximum(np.abs(np.diff(targets,axis=0))/dt-k.velocity,0).max())
    phases={}
    for phase in dict.fromkeys(trace['phase']):
        sel=trace['phase']==phase;item=dict(frames=int(sel.sum()),
            object_max_height_m=float(trace['object'][sel,2].max()),object_end=trace['object'][sel][-1].tolist())
        for field in ['finger_table_contacts','finger_knife_contacts']:
            if field in trace:item[field+'_frames']=(trace[field][sel]>0).sum(0).tolist()
        phases[str(phase)]=item
    out['phases']=phases
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('runs/g2-tabletop-v1'));a=p.parse_args()
    rows=[]
    for path in sorted(a.root.iterdir()):
        if not (path/'trace.npz').exists() or not (path/'report.json').exists():continue
        try:rows.append(audit(path))
        except (KeyError,ValueError) as e:rows.append(dict(name=path.name,audit_error=str(e)))
    (a.root/'trajectory-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='phases'} for r in rows],indent=2))


if __name__=='__main__':main()
