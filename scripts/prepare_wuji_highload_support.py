"""Spread initial support sites across handle width, retaining thumb and preload.

This is a geometry hypothesis, not an actual contact-area/force certificate.
All sites use original collision hulls and initial estimated knife coordinates.
No physical state is changed after reset; full acquisition must be certified.
"""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry

def main():
    p=argparse.ArgumentParser();p.add_argument('--spread-m',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert 0<a.spread_m<=.004
    a.output.mkdir(parents=True,exist_ok=False);base=Path('runs/wrap-force-20261004/planning/source-bounded-index-wrap-v8/direct-corner-v6');plan=json.loads((base/'motor-plan.json').read_text());g=DigitGeometry();w=np.asarray(plan['wrist_in_knife']);touch=np.asarray(plan['touch_q']);new=touch.copy();rows=[]
    for finger,delta in [('index',-a.spread_m),('middle',a.spread_m/2),('pinky',a.spread_m)]:
        ids=[g.w.names.index('hand_r_'+finger+'_joint'+str(i)) for i in range(1,5)];link='hand_r_'+finger+'_pad_link';vertices=np.concatenate([v for v,_ in g.meshes[link]])
        def point(q):
            m=w@g.w.forward(q)[link];v=vertices@m[:3,:3].T+m[:3,3];weights=np.exp((v[:,1]-v[:,1].max())/.0002);return weights@v/weights.sum(),m[:3,0]
        original,normal=point(touch);target=original+np.array([delta,0,0])
        def residual(x):
            q=touch.copy();q[ids]=x;pos,n=point(q);return np.r_[(pos-target)*200,(n-normal)*.12,(x-touch[ids])*.002]
        fit=least_squares(residual,touch[ids],bounds=(g.w.lower[ids]+.005,g.w.upper[ids]-.005),max_nfev=200)
        new[ids]=fit.x;pos,n=point(new);error=float(np.linalg.norm(pos-target));assert error<.00025,(finger,error)
        rows.append(dict(finger=finger,initial_motor_surface_point_m=original.tolist(),new_motor_surface_point_m=pos.tolist(),requested_lateral_shift_m=delta,error_m=error))
    shift=new-touch;result=copy.deepcopy(plan);result['touch_q']=new.tolist()
    for key in ['open_q','close_q']:result[key]=np.clip(np.asarray(plan[key])+shift,g.w.lower+.005,g.w.upper-.005).tolist()
    result['close_waypoints']=[dict(fraction=0.,q=result['open_q']),dict(fraction=2/3,q=result['touch_q']),dict(fraction=1.,q=result['close_q'])]
    result['support_spread_geometry']=dict(scope=__doc__,spread_m=a.spread_m,sites=rows)
    result['geometric_pass']=False
    for key in ['selected_contact_gaps_m','selected_pad_gaps_m','minimum_knife_gap_m','minimum_table_gap_m','equilibrium_audit']:result.pop(key,None)
    (a.output/'motor-plan.json').write_text(json.dumps(result,indent=2))
    for name in ['localization.json','calibration.json']:(a.output/name).write_bytes((base/name).read_bytes())
    (a.output/'geometry.json').write_text(json.dumps(result['support_spread_geometry'],indent=2));print(json.dumps(result['support_spread_geometry']))
if __name__=='__main__':main()
