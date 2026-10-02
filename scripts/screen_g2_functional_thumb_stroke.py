"""Screen scheduled thumb travel from a calibrated functional grasp, without physics.

Other fingers stay at touch geometry. No slider/controller state is read at runtime:
the slider displacement here is an offline hypothesis used for collision checking.
This is reachability evidence, never evidence of pressure or operation success.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    j=json.loads(a.plan.read_text());g=DigitGeometry(knife_spec=a.knife_spec);h=g.w;q=np.array(j['touch_q'],dtype=float);w=np.array(j['wrist_in_knife']);link='hand_r_thumb_pad_link';normal=np.array(j['contact_normals'][0]);ids=np.array([h.names.index('hand_r_thumb_joint'+str(n)) for n in range(1,5)])
    mat=w@h.forward(q)[link];vertices=np.concatenate([v for v,_ in g.meshes[link]]);points=vertices@mat[:3,:3].T+mat[:3,3];proj=points@normal;weight=np.exp(-(proj-proj.min())/.0002);weight/=weight.sum();anchor=weight@vertices;start=weight@points;seed=q[ids].copy();rows=[]
    def calculate(values):
        full=q.copy();full[ids]=values;t=w@h.forward(full)[link];return t[:3,:3]@anchor+t[:3,3],t[:3,0],full
    start_normal=calculate(seed)[1]
    for shift in np.linspace(0,.04,41):
        target=start+np.array([0,0,shift]);prior=seed.copy()
        def residual(values):
            point,facing,_=calculate(values);return np.r_[(point-target)*250,(facing-start_normal)*.2,(values-prior)*.005]
        fit=least_squares(residual,np.clip(seed,h.lower[ids]+1e-7,h.upper[ids]-1e-7),bounds=(h.lower[ids],h.upper[ids]),max_nfev=100,diff_step=1e-5);seed=fit.x;point,facing,full=calculate(seed)
        row=dict(shift_m=float(shift),q_thumb=seed.tolist(),point_error_m=float(np.linalg.norm(point-target)),pad_facing_cosine=float(facing@(-normal)),limit_margin_rad=float(np.minimum(seed-h.lower[ids],h.upper[ids]-seed).min()))
        if round(shift*1000)%5==0:
            gaps=g.gaps(full,w,j['planning_slider_m']+shift);row.update(thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),thumb_slider_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1'),thumb_other_finger_gap_m=min(v['gap_lower_bound_m'] for v in g.self_gaps(full,'thumb')))
        rows.append(row)
    result=dict(source=str(a.plan),scope='Offline reach/collision hypothesis only, no actual pressure, no pickup or operation success',contact_link=link,anchor_local=anchor.tolist(),point_start_m=start.tolist(),wrist_in_knife=w.tolist(),rows=rows)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(max_point_error_m=max(v['point_error_m'] for v in rows),end=rows[-1])))
if __name__=='__main__':main()
