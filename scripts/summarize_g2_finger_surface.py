"""Read measured new-grasp trials; never infer policy success from pickup."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


def summarize(folder):
    file=folder/'trace.npz'
    if not file.exists():file=folder/'partial-trace.npz'
    if not file.exists():return dict(name=folder.name,status='no_completed_trace')
    t=np.load(file);phases=[];names=list(dict.fromkeys(t['phase']))
    for phase in names:
        ix=np.flatnonzero(t['phase']==phase);late=ix[-30:]
        world=t['object'][ix];wrists=t['wrist'][ix]
        rel=np.asarray([np.linalg.inv(transform(w[:3],w[3:]))@transform(o[:3],o[3:]) for w,o in zip(wrists,world)])
        translation=np.linalg.norm(rel[:,:3,3]-rel[0,:3,3],axis=1)
        angle=Rotation.from_matrix(rel[0,:3,:3].T@rel[:,:3,:3]).magnitude()
        departed=np.flatnonzero((translation>=.01)|(angle>=.25))
        phases.append(dict(phase=str(phase),start_s=float(t['time'][ix[0]]),end_s=float(t['time'][ix[-1]]),
            min_object_z_m=float(world[:,2].min()),max_object_z_m=float(world[:,2].max()),
            hand_translation_from_phase_start_max_m=float(translation.max()),hand_rotation_from_phase_start_max_rad=float(angle.max()),
            first_10mm_or025rad_hand_departure_s=float(t['time'][ix[departed[0]]]) if len(departed) else None,
            last_second_finger_contact_fraction=(t['finger_knife_contacts'][late]>0).mean(0).tolist(),
            last_second_all_five_contact_fraction=float((t['finger_knife_contacts'][late]>0).all(1).mean()),
            finger_table_contact_frames=(t['finger_table_contacts'][ix]>0).sum(0).tolist(),
            knife_table_contact_frames=int((t['knife_table_contacts'][ix]>0).sum()),
            slider_start_m=float(t['slider'][ix[0]]),slider_end_m=float(t['slider'][ix[-1]]),
            slider_range_m=float(np.ptp(t['slider'][ix])),
            diagnostic='Phase-start hand-relative movement, not a success score during planned regrasp'))
    out=dict(name=folder.name,trace=str(file),control_frames=len(t['time']),duration_s=float(t['time'][-1]),
        contact_order=['thumb','index','middle','ring','pinky'],phases=phases,
        entered_policy=bool(np.any(t['phase']=='operate')),
        slider_motor_target_constant=bool(np.ptp(t['reference_targets'][:,-1])==0),
        measured_effort_available=bool(np.isfinite(t['dof_effort']).any()),
        operation_success=None,whole_success=False)
    for key in ['pickup-hold-check','air-flip-check','failure','report']:
        p=folder/(key+'.json')
        if p.exists():out[key.replace('-','_')]=json.loads(p.read_text())
    if out['entered_policy']:
        out['operation_success']=out.get('report',{}).get('operation_window_success',out.get('report',{}).get('required_task_success'))
        out['whole_success']=out.get('report',{}).get('whole_success',False)
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists(),'Preserve earlier audit output'
    rows=[summarize(folder) for folder in a.run]
    a.output.write_text(json.dumps(dict(trials=rows,scope='Development, no new-placement validation; no operation inference from acquisition'),indent=2)+'\n')
    print(json.dumps([dict(name=r['name'],entered_policy=r.get('entered_policy'),pickup=r.get('pickup_hold_check',{}).get('retained'),
        flip=r.get('air_flip_check',{}).get('retained'),whole=r.get('whole_success'),failure=r.get('failure',{}).get('message')) for r in rows]))


if __name__=='__main__':main()
