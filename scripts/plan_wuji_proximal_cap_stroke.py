"""Check a proximal slider contact against the current acquired support layout.

Geometry only: point error and clearance never count as an actual push. The
purpose is to avoid moving a loaded bearing when changing the thumb start
point can supply the needed longitudinal reaction lever.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--start-z',type=float,default=-.036)
    p.add_argument('--start-current-point',action='store_true')
    p.add_argument('--stroke',type=float,default=.022);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);s=np.load(a.source/'takeover.npz')
    trial,native,end=source_contacts(a.source)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();checker=HandIntersection();q0=s['robot_q'][7:].astype(float)
    O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);name='hand_r_thumb_pad_link'
    cs=[v for r in native for v in r['contacts'] if v['hand_link']==name and v['knife_link']=='link_1']
    m=np.mean([v['position_hand_link_m'] for v in cs],0)
    T=L@g.w.forward(q0)[name];P0=T[:3,:3]@m+T[:3,3]
    if a.start_current_point:a.start_z=float(P0[2])
    n=np.sum([v['force_normal_contribution_knife_N'] for v in cs],0);n/=np.linalg.norm(n);local=T[:3,:3].T@n
    e=record('proximal_cap_capacity_start',[str(a.output)],config=dict(candidate='C560-R11',source=str(a.source),
        thumb_start_z_m=a.start_z,stroke_m=a.stroke,unchanged_support_layout='actual Ipad/Mpad/M4/Ring4',
        uncertainty='Can a proximal cap contact leave22mm fixedwrist travel while current bearings straddle the loaded thumb better?',
        decision='Feasible -> short thumb release/reacquire without moving loadedMiddle; blocked -> minimum coordinatedgrip change, no native on infeasible geometry'),next_step='Proximal functional grip geometry, not fixed old Thumbmaterial requirement')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    started=time.time();q=q0.copy();rows=[]
    for shift in np.linspace(0,a.stroke,9):
        target=P0.copy();target[2]=a.start_z+shift;slider=float(s['slider_q'])+shift
        def residual(x):
            h=q0.copy();h[16:]=x;F=g.w.forward(h);T=L@F[name];P=T[:3,:3]@m+T[:3,3];r=list((P-target)*500)
            r.extend((T[:3,:3]@local-n)*.15)
            for gap in g.gaps(h,L,slider,'thumb',frames=F):
                threshold=-.00025 if gap['hand_link']==name and gap['knife_link']=='link_1' else .0003
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*700)
            r.extend(min(0,v['gap_lower_bound_m']-.0002)*250 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0002,frames=F))
            r.extend((x-q[16:])*.015);return np.array(r)
        fit=least_squares(residual,np.clip(q[16:],g.w.lower[16:]+.035+1e-7,g.w.upper[16:]-.035-1e-7),
            bounds=(g.w.lower[16:]+.035,g.w.upper[16:]-.035),max_nfev=80,diff_step=1e-5)
        q[16:]=fit.x;T=L@g.w.forward(q)[name];P=T[:3,:3]@m+T[:3,3];gaps=g.gaps(q,L,slider,'thumb')
        rows.append(dict(shift_m=float(shift),target_knife_m=target.tolist(),point_knife_m=P.tolist(),point_error_m=float(np.linalg.norm(P-target)),
            hand_q=q.tolist(),thumb_normal=(T[:3,:3]@local).tolist(),self_intersections=checker.inspect(q),
            min_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
            min_housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!=name)))
    r=dict(source=str(a.source),material_link=name,material_point=m.tolist(),material_normal_local=local.tolist(),
        thumb_start_z_m=a.start_z,stroke_m=a.stroke,rows=rows,elapsed_s=time.time()-started,scope=__doc__)
    r['permits_path']=all(v['point_error_m']<.0005 and not v['self_intersections'] and v['min_body_gap_m']>.0001 and v['min_housing_cap_gap_m']>.0001 for v in rows)
    (a.output/'geometry.json').write_text(json.dumps(r,indent=2))
    summary=dict(permits_path=r['permits_path'],max_point_error_m=max(v['point_error_m'] for v in rows),
        min_body_gap_m=min(v['min_body_gap_m'] for v in rows),min_housing_cap_gap_m=min(v['min_housing_cap_gap_m'] for v in rows),
        self_frames=sum(bool(v['self_intersections']) for v in rows),source=str(a.source),elapsed_s=r['elapsed_s'])
    print(json.dumps(summary),flush=True)
    e=record('proximal_cap_capacity_terminal',[str(a.output/'geometry.json')],config=summary,
        next_step='Eligibleproximal actualThumb reacquisition thennative22mm; infeasible -> modify operationgrip with specificgeometry rather than more pressure')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')


if __name__=='__main__':main()
