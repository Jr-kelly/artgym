"""Withdraw the actual loaded thumb; retain all acquired nonthumb commands.

The native experiment decides support, not a normal-force sum or this IK.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--whole-thumb-clearance',action='store_true')
    p.add_argument('--released-hand-prior',type=Path)
    p.add_argument('--outward-first',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz')
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    q=s['robot_q'][7:].astype(float)
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    _,native,end=source_contacts(a.source);name='hand_r_thumb_link4'
    cs=[c for r in native if r['time_s']>end-.15 for c in r['contacts'] if c['hand_link']==name and c['knife_link']=='link_0']
    m=np.mean([c['position_hand_link_m'] for c in cs],axis=0)
    def point(h):
        T=L@g.w.forward(h)[name];return T[:3,:3]@m+T[:3,3]
    start=point(q);seed=q[16:].copy();rows=[];D=[];checker=HandIntersection()
    gaps0=g.gaps(q,L,float(s['slider_q']),'thumb')
    released=np.array(json.loads(a.released_hand_prior.read_text())) if a.released_hand_prior else None
    if released is not None:
        shadow=q.copy();shadow[:16]=released[:16]
        shadow_gaps0={(v['moving_link'],v['other_link']):v['gap_lower_bound_m'] for v in g.self_gaps(shadow,'thumb',certify_clearance_m=.0008)}
    record('direct_thumb_withdrawal_start',[str(a.output)],config={'source':str(a.source),'uncertainty':'Can genuine backcorner I/M/R support retain knife after removing thumb?','change':'Only thumb 12mm outward, acquired load decays during withdrawal; other commands fixed'},next_step='Native no-thumb support -> actual cap approach; first loss -> change support topology')
    for t in np.linspace(0,4.5,46):
        u=smooth((t-.4)/2.5);target=start+np.array([-.018,.008,0] if a.whole_thumb_clearance else [-.012,0,0])*u
        if a.outward_first:
            # Avoid unfolding the pad beside the loaded index. Clear sideways
            # first, then use the free space above the knife.
            target=start+np.array([-.018*smooth(u/.7),.008*smooth((u-.7)/.3),0])
        def residual(x):
            h=q.copy();h[16:]=x
            r=list((point(h)-target)*300);r.extend((x-seed)*.015)
            if a.whole_thumb_clearance:
                release=smooth(u/.8)
                for v,old in zip(g.gaps(h,L,float(s['slider_q']),'thumb'),gaps0):
                    threshold=(1-release)*min(.002,old['gap_lower_bound_m'])+release*.002
                    r.append(min(0,v['gap_lower_bound_m']-threshold)*1500)
                r.extend(min(0,v['gap_lower_bound_m']-.0001)*200 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0001))
            if released is not None:
                # The observed loaded index shifts after thumb release. Keep
                # that actual shape as a planning obstacle, without issuing
                # a nonthumb pose or assigning simulator state.
                shadow=h.copy();shadow[:16]=released[:16];blend=smooth(u/.5)
                for v in g.self_gaps(shadow,'thumb',certify_clearance_m=.0008):
                    old=shadow_gaps0.get((v['moving_link'],v['other_link']),.0008)
                    threshold=(1-blend)*min(.0008,old)+blend*.0008
                    r.append(min(0,v['gap_lower_bound_m']-threshold)*1500)
            return np.array(r)
        if u>0:
            fit=least_squares(residual,np.clip(seed,g.w.lower[16:]+.05,g.w.upper[16:]-.05),bounds=(g.w.lower[16:]+.05,g.w.upper[16:]-.05),max_nfev=70,diff_step=1e-5);seed=fit.x
        h=q.copy();h[16:]=seed;cmd=s['issued_target'][7:].astype(float)
        cmd[16:]=seed+(s['issued_target'][23:]-q[16:])*(1-u)
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
        D.append(dict(time_s=float(t),fraction=float(u),error_m=float(np.linalg.norm(point(h)-target)),planned_hand_q=h.tolist(),self=checker.inspect(h),thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(h,L,float(s['slider_q']),'thumb') if v['knife_link']=='link_0')))
    rate=float(abs(np.diff(np.array([d['planned_hand_q'] for d in D]),axis=0)/.1).max())
    result=dict(rows=rows,diagnostics=D,source=str(a.source),released_hand_prior=str(a.released_hand_prior),material_point=m.tolist(),development_abort_on_translation_m=.025,maximum_planned_rate_rad_s=rate,maximum_error_m=max(d['error_m'] for d in D),self_frames=sum(bool(d['self']) for d in D),terminal_thumb_body_gap_m=D[-1]['thumb_body_gap_m'],scope=__doc__)
    result['preflight_pass']=result['maximum_error_m']<.0005 and not result['self_frames'] and result['terminal_thumb_body_gap_m']>.0019 and rate<1.
    (a.output/'motor.json').write_text(json.dumps(result,indent=2));summary={k:v for k,v in result.items() if k not in ['rows','diagnostics']};print(json.dumps(summary))
    record('direct_thumb_withdrawal_prepared',[str(a.output/'motor.json')],config=summary,next_step='Passing clearance -> one native no-thumb support test, then actual cap entry')
    if not result['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
