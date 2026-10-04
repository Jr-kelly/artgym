"""Certify one signed original joint corridor; configure paused tracking search."""
import copy,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');O=B/'ring-tracking-acquisition-v1';O.mkdir(exist_ok=False);source=B/'postlift-ring-brace-v1/motor-plan-staged.json';plan=json.loads(source.read_text());plan['post_lift_preload_seconds']=[12.,13.];path=O/'motor-plan.json';path.write_text(json.dumps(plan,indent=2));g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;w=np.asarray(plan['wrist_in_knife']);start=np.asarray(plan['post_lift_close_q']);vertices=np.concatenate([v for v,_ in g.meshes['hand_r_ring_pad_link']]);normal=np.array([0.,-1.,0.]);ids=[h.names.index('hand_r_ring_joint%d'%i) for i in range(1,5)]
def surface(q):
 m=w@h.forward(q)['hand_r_ring_pad_link'];v=vertices@m[:3,:3].T+m[:3,3];projection=v@normal;weights=np.exp(-(projection-projection.min())/.0002);weights/=weights.sum();return weights@v
derivatives=[]
for index in ids:
 high=start.copy();low=start.copy();high[index]+=1e-5;low[index]-=1e-5;derivatives.append(float((surface(high)[1]-surface(low)[1])/2e-5))
index=ids[int(np.argmax(np.abs(derivatives)))];sign=1 if derivatives[ids.index(index)]>0 else -1;maximum=.04;ref=json.loads((B/'initial-geometry-v2/projected-00/reference-v1.json').read_text());shifts=np.array([row['shift_m'] for row in ref['rows']]);thumb=np.array([row['q_thumb'] for row in ref['rows']]);rows=[]
# New ring corridor only; current thumb/otherfinger reference unchanged. Original
# full161 nominal thumb certificate and21 transfer are retained separately.
for offset in np.linspace(0,maximum,9):
 for shift in np.linspace(0,.04,41):
  q=start.copy();q[index]+=sign*offset;q[16:]+=np.array([np.interp(shift,shifts,thumb[:,i]) for i in range(4)])-thumb[0];gaps=g.self_gaps(q,'ring',certify_clearance_m=.000015)+g.self_gaps(q,'thumb',certify_clearance_m=.000015);minimum=min(r['gap_lower_bound_m'] for r in gaps);margin=float(np.minimum(q-h.lower,h.upper-q).min());rows.append(dict(offset_rad=float(offset),shift_m=float(shift),minimum_self_gap_m=float(minimum),minimum_limit_margin_rad=margin,passed=margin>=.005-1e-7 and minimum>=.000015-1e-7))
passed=all(row['passed'] for row in rows);spec={'format':'wuji-joint-tracking-contact-acquisition-v1','digit':'ring','hand_index':index,'hand_joint_name':h.names[index],'anchor_rad':float(start[index]),'inward_motor_sign':sign,'normal_surface_derivative_m_per_rad':derivatives[ids.index(index)],'maximum_motor_offset_rad':maximum,'motor_step_rad':.0015,'search_interval_seconds':[13.2,14.3],'tracking_lag_threshold_rad':.01,'filter_frames':5,'consecutive_proxy_frames':3,'all_requested_corridor_passed':passed,'motor_plan_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Onebounded original.04rad corridor, chosenby onceknownpadnormalFK only, no body/force truth. Paused signed issued-minus-measured tracking verification is a loadproxy, not measurednormalforce/contactownership orconstantforce. Freeze14.3 before50actualmeasuredhistoryframes; no actor/R800feature orgravity/torque change.'};(O/'corridor-audit.json').write_text(json.dumps({'passed':passed,'rows':rows,'joint_normal_derivatives':derivatives},indent=2));(O/'config.json').write_text(json.dumps(spec,indent=2));record('ring_tracking_acquisition_original_corridor_prepared',config=spec,evidence=str(O),next='Onechanged12--13transfer geometrygate then actual.5/.5 36s ifalloriginalcorridorpasses; no motorrange/lagthreshold sweep');print(json.dumps(spec));assert passed,'Reject originalself/limit corridor; no physicaltest'
