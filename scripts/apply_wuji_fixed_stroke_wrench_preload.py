"""Restore the requested wrench feedforward truncated by a legacy angle cap.

Only existing motor rows change. Original force reference, feedback, physical
PD, effort, friction and collisions are retained. Native validation is required.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['motor','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--maximum-preload-rad',type=float,default=.30)
    p.add_argument('--coordinated-frames',action='store_true',help='Use each knot actual planned wrist/knife frame for a coordinated path')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    d=json.loads(a.motor.read_text());s=np.load(Path(d['source'])/'takeover.npz')
    cfg=d['direct_pressure_path_servo'];kp=np.array(cfg['thumb_kp']);effort=np.array(cfg['thumb_effort'])
    trial=Path(json.load(open(Path(d['source'])/'manifest.json'))['source']).parent
    kd=np.array(json.load(open(trial/'physics.json'))['kd'])[-4:]
    w=WujiKinematics();L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    material=np.array(cfg['material_point']);q0=s['robot_q'][7:].astype(float)
    times=np.array([r['time_s'] for r in d['rows']]);hands=np.array([r['planned_hand_q'] for r in d['diagnostics']]);velocity=np.gradient(hands[:,16:],times,axis=0)
    stats=[]
    record('fixed_stroke_requested_wrench_preload_start',[str(a.output),str(a.motor)],config={'uncertainty':'Legacy120mrad preload plus80mrad correction saturates below requested axial proxy despite ample original effort reserve; preserving requested wrench restores useful travel?','maximum_preload_rad':a.maximum_preload_rad},next_step='Native sameactual source, unchanged wrench references/feedback; enough travel -> fullfresh')
    for i,(row,q) in enumerate(zip(d['rows'],hands)):
        if a.coordinated_frames:
            knot=d['diagnostics'][i]
            expected=np.array(knot.get('expected_object_world',knot['planned_object_world']))
            L=np.linalg.inv(expected)@G2Kinematics().forward(np.array(knot['planned_arm_q']))
        def point(h):
            T=L@w.forward(h)['hand_r_thumb_pad_link'];return T[:3,:3]@material+T[:3,3]
        P=point(q);J=np.empty((3,4))
        for j in range(4):
            h=q.copy();h[16+j]+=1e-5;J[:,j]=(point(h)-P)/1e-5
        t=row['time_s'];force=np.array([0,-cfg['normal_reference_N'],cfg['axial_reference_N']*smooth((t-.5)/1.5)])
        tau=J.T@force
        if np.max(abs(tau)/effort)>.5:raise ValueError('Requested wrench exceeds selected 50 percent original effort guard')
        preload=np.clip(tau/kp,-a.maximum_preload_rad,a.maximum_preload_rad)
        blend=smooth(t);h=np.array(row['hand_q']);h[16:]=q[16:]+(s['issued_target'][23:]-q0[16:])*(1-blend)+preload*blend+np.clip(kd/kp*velocity[i],-.07,.07)
        h[16:]=np.clip(h[16:],w.lower[16:]+.02,w.upper[16:]-.02);row['hand_q']=h.tolist()
        stats.append(dict(time_s=t,requested_preload_rad=(tau/kp).tolist(),requested_effort_fraction=(abs(tau)/effort).tolist()))
    summary=dict(max_requested_preload_rad=max(max(abs(np.array(r['requested_preload_rad']))) for r in stats),max_requested_effort_fraction=max(max(r['requested_effort_fraction']) for r in stats),source_jump_rad=float(abs(np.r_[d['rows'][0]['arm_q'],d['rows'][0]['hand_q']]-s['issued_target']).max()),old_truncated_rows=sum(any(abs(np.array(r['requested_preload_rad']))>.12) for r in stats),new_truncated_rows=sum(any(abs(np.array(r['requested_preload_rad']))>a.maximum_preload_rad) for r in stats))
    if summary['source_jump_rad']>1e-6:raise ValueError('Source command jump')
    d['wrench_preload_repair']=dict(summary=summary,maximum_preload_rad=a.maximum_preload_rad,coordinated_frames=a.coordinated_frames,diagnostics=stats,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(d,indent=2));print(json.dumps(summary))
    record('fixed_stroke_requested_wrench_preload_terminal',[str(a.output/'motor.json')],config=summary,next_step='Native unchangedactual source tests requested wrench truncation repair, no force gain increase')

if __name__=='__main__':main()
