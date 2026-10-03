"""Two nominal post-lift support layouts; actual collision rollout decides feasibility.

Only previously calibrated nominal geometry enters this offline planner. Neither
physical variant identity nor current object/contact truth selects motor targets.
"""
import json, pathlib, subprocess, sys
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry

R=pathlib.Path(__file__).resolve().parents[2]
D=R/'research/support-pressure-20261003'
base=json.loads((R/'research/robust-knife-family-20261003/functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text())
g=DigitGeometry(); h=g.w; wrist=np.asarray(base['wrist_in_knife']); normals=np.asarray(base['contact_normals'])

def point(q, finger):
    i=['thumb','index','middle','ring','pinky'].index(finger)
    m=wrist@h.forward(q)['hand_r_'+finger+'_pad_link']
    v=np.concatenate([v for v,_ in g.meshes['hand_r_'+finger+'_pad_link']])@m[:3,:3].T+m[:3,3]
    p=v@normals[i]; w=np.exp(-(p-p.min())/.0002); w/=w.sum()
    return w@v, m[:3,0]

for label,fingers in [('middle-inward',['middle']),('middle-pinky-inward',['middle','pinky'])]:
    q=np.asarray(base['touch_q']).copy(); audits=[]
    for finger in fingers:
        idx=[h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)]
        original,axis=point(q,finger); target=original+np.array([.0035,0,0]); seed=q.copy()
        def residual(x):
            candidate=seed.copy();candidate[idx]=x
            p,n=point(candidate,finger)
            return np.r_[(p-target)*100,(n-axis)*.12,(x-seed[idx])*.002]
        fit=least_squares(residual,seed[idx],bounds=(h.lower[idx]+.0001,h.upper[idx]-.0001),max_nfev=200)
        q[idx]=fit.x;p,n=point(q,finger)
        audits.append(dict(finger=finger,original=original.tolist(),target=target.tolist(),actual=p.tolist(),error_m=float(np.linalg.norm(p-target)),q=fit.x.tolist()))
    out=D/(label+'-v16');out.mkdir(exist_ok=False)
    plan=dict(base);plan['touch_q']=q.tolist();plan['support_layout_audit']=audits
    (out/'touch-plan.json').write_text(json.dumps(plan,indent=2))
    subprocess.run([sys.executable,'-m','scripts.plan_g2_contact_equilibrium','--plan',str(out/'touch-plan.json'),'--calibration','research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json','--output',str(out/'equilibrium'),'--thumb-normal','1.5','--closed-slider-passive-limit'],cwd=R,check=True,stdout=(out/'planner.log').open('w'))
    fitted=json.loads((out/'equilibrium/motor-plan.json').read_text())
    target=np.asarray(fitted['close_q']);target=np.clip(q+1.25*(target-q),h.lower+.0001,h.upper-.0001)
    config=dict(post_lift_target_q=target.tolist(),ring_target_q=None,thumb_preload_delta_q=[0,0,0,0],transition_seconds=[12,14],scope='Nominal inward underside contact geometry plus static coordinated impedance targets; physical force not prescribed. Same fixed profile for every variant. Original pickup unchanged.',support_layout_audit=audits)
    (D/(label+'-v16.json')).write_text(json.dumps(config,indent=2));print(label,audits,flush=True)
