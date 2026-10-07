"""Release thumb by opening its base, retaining current issued carrier commands."""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['source','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--opening-rad',type=float,default=.2)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float)
    issued=s['issued_target'][7:].astype(float)
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    c=HandIntersection();rows=[];D=[]
    record('acquired_thumb_release_path_start',[str(a.output)],config={'source':str(a.source),'opening_rad':a.opening_rad,'uncertainty':'Current reserved carrier commands retain nonthumb support after thumb base opens?'},next_step='Native free-thumb support and current reserve; then functional cap entry')
    for t in np.linspace(0,3,31):
        u=smooth(t/1.5);q=q0.copy();q[16]-=a.opening_rad*u
        h=issued.copy();h[16:]=q[16:]+(issued[16:]-q0[16:])*(1-u)
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=h.tolist()))
        D.append(dict(time_s=float(t),self=c.inspect(q),body_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(q,L,float(s['slider_q']),'thumb') if v['knife_link']=='link_0'),planned_thumb_q=q[16:].tolist()))
    guard=dict(self_frames=sum(bool(v['self']) for v in D),minimum_body_gap_m=min(v['body_gap_m'] for v in D),terminal_body_gap_m=D[-1]['body_gap_m'],source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),nonthumb_motor_const=all(np.array_equal(v['hand_q'][:16],issued[:16]) for v in rows),min_planned_thumb_margin_rad=float(min(np.minimum(np.array(v['planned_thumb_q'])-g.w.lower[16:],g.w.upper[16:]-np.array(v['planned_thumb_q'])).min() for v in D)))
    guard['preflight_pass']=guard['self_frames']==0 and guard['minimum_body_gap_m']>.0001 and guard['source_jump_rad']<1e-6 and guard['min_planned_thumb_margin_rad']>.02
    out=dict(rows=rows,diagnostics=D,guard=guard,source=str(a.source),development_abort_on_translation_m=.012,scope=__doc__+' Original finite PD/effort/collision; no native force feedback.')
    (a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps(guard))
    record('acquired_thumb_release_path_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing geometry -> native3s; actual nonthumb support and margin decide cap reentry')
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
