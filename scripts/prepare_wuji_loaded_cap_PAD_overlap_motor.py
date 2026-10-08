"""Verify valid loaded-roll prefix then preserve original measured motor offsets.

Chosen geometry stops in LINK4/PAD cap contact overlap. Original wrist/Index/idle
issued targets are retained. Captured offset is a finite motor reference, never a
constant force or full carry proof. Native PAD load must precede old clamp exit.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_exact_knife_intersection import exact_hand_knife_intersection
p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',type=int,default=943);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.load(open(a.geometry));path=[r for r in geo['rows']if r['phase']<=.5];assert len(path)>=11 and path[-1]['contact_overlap_required'] and not any(r['self']or r['geometry_violations']for r in path);src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);L=np.array(path[0]['wrist_in_knife']);depth=min(-.0002,path[0]['LINK4_cap_gap_m']-.00002);failure=None;samples=[];exact_checks=[];record('actual_loaded_cap_PAD_overlap_motor_precheck_started_v%d'%a.version,[str(a.geometry)],dict(scope=__doc__,selected_last_phase=path[-1]['phase'],source_cap_depth_m=depth,original_pd_effort=True),next_step='Densewholethumb cap/body/H +motorbounds, one actualoverlap carrying test; do notexitLINK4 beforeactualPADsupport')
for seg,(A,B)in enumerate(zip(path[:-1],path[1:])):
 A=np.array(A['hand_q']);B=np.array(B['hand_q']);n=max(2,int(np.ceil(abs(B-A).max()/.008))+1)
 for u in np.linspace(0,1,n):
  h=A*(1-u)+B*u;H=f.H.inspect(h);G=g.gaps(h,L,float(z['slider_q']),'thumb',certify_clearance_m=.0002);viol=[c for c in G if c['gap_lower_bound_m']<(depth if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link']else -.00001)];confirmed=[]
  for collision in viol:
   certificate=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),collision);exact_checks.append(dict(segment=seg,fraction=float(u),**certificate))
   if not certificate['no_intersection']:confirmed.append(collision)
  viol=confirmed;cap4=next(c['gap_lower_bound_m']for c in G if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']=='hand_r_thumb_link4');samples.append(dict(segment=seg,fraction=float(u),self=H,violations=viol,LINK4_cap_gap_m=cap4))
  if H or viol or cap4>.0002:failure='Denseoriginalhull/H/oldcapcontact';break
 if failure:break
rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,1.]];clock=1.;previous=issued[7:].copy()
if failure is None:
 for p in path:
  h=np.array(p['hand_q']);motor=issued[7:].copy();motor[16:]=h[16:]+issued[23:]-h0[16:]
  if np.minimum(motor-g.w.lower,g.w.upper-motor).min()<=0:failure='Originalmotorbound';break
  clock+=max(1,int(np.ceil(abs(motor-previous).max()/.012)))/30.;rows.append(dict(time_s=clock,arm_q=issued[:7].tolist(),hand_q=motor.tolist()));previous=motor
out=dict(passed=failure is None,failure=failure,samples=samples,exact_mesh_fallback=exact_checks,scope=__doc__,seconds=clock+1.5);(a.output/'precheck.json').write_text(json.dumps(out,indent=2))
if failure is None:
 rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
record('actual_loaded_cap_PAD_overlap_motor_precheck_terminal_v%d'%a.version,[str(a.output/'precheck.json')],dict(passed=out['passed'],failure=failure,dense_samples=len(samples),seconds=clock+1.5),next_step='Validfirstoverlap native PADnormal >=1s andH/quietoldclamp; thencompletefunctionalPADsurface approach/fullB30 andfreshsameepisode timely');print(json.dumps({k:v for k,v in out.items()if k!='samples'}))
