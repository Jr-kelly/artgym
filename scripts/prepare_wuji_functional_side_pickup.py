"""Clear and execute one changed longitudinal opposing-side tabletop layout.

D707 is a geometric prior. Its same-wrist cap endpoint is blocked, so initial
and operating grips are not frozen together. This prepares only fresh pickup;
any following wrist/finger adjustment must consume that pickup's actual state.
"""
import json,time,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def note(event, evidence, cfg, next_step):
 e=record(event,evidence,config=cfg,next_step=next_step)
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(cfg)+'\n')


def main():
 B=Path('runs/flat-table-20261006/direct');source=B/'preparation/direct-functional-joint-opposed-grip-v707/candidate.json';out=B/'preparation/direct-functional-clear-side-pickup-v708';out.mkdir(exist_ok=False);c=json.loads(source.read_text());g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));check=HandIntersection();k=G2Kinematics();q0=np.asarray(c['poses'][0]['hand_q']);L=np.asarray(c['wrist_in_knife']);O=np.asarray(c['table_object_world']);W=O@L;ids=np.r_[0:8,12:20];names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4'];dirs={names[0]:np.array([1.,0,0]),names[1]:np.array([0,1.,0]),names[2]:np.array([-1.,0,0])};V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in names};parts=g.knife_geometry.collision_parts(0.)
 cfg=dict(candidate='D708',grasp_end='Pendingnewfreshnative,707geometry only',support_layout='LongitudinalIndex-X/Ring+Xsideopposition plusMiddleback; Thumbfree, no forced2/3finger rule',control='Localwholehand table/selfprojection, originalnormalmagnitude .9Nside/.15Nback but nowopposeddirections balanced; no physics/PD/effort/friction/resistancelimits changes',uncertainty='Can actualopposedsidecontacts, insteadof earlierRingdownwardcornerload, lift55g whileleaving futureThumbroom?',decision='Clearapproach -> fresh9s native once; actualsafefreebearing -> ownwrist/Thumbadaptation. Firstremainingfailure guideschange, no fixedLcap/forcebias retries',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 note('functional_side_pickup_preparation_start',[str(source),str(out),'scripts/prepare_wuji_functional_side_pickup.py'],cfg,cfg['decision'])
 def surface(h,n):
  F=g.w.forward(h);T=L@F[n];v=V[n]@T[:3,:3].T+T[:3,3];s=v@dirs[n];weights=np.exp((s-s.max())/.00015);m=weights@V[n]/weights.sum();return T[:3,:3]@m+T[:3,3],m
 prior={n:surface(q0,n)[0] for n in names}
 def common(h):
  F=g.w.forward(h);r=[]
  for n,p in g.meshes.items():
   T=W@F[n];r.extend(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7506))*1200 for v,_ in p)
  r.extend(min(0.,a['gap_lower_bound_m']-.0003)*900 for a in g.pair_gaps(h,check.pairs,certify_clearance_m=.0003))
  for digit in ['index','middle','ring','thumb']:
   for a in g.gaps(h,L,0.,digit,frames=F,knife_parts=parts,certify_clearance_m=.0003):
    bearing=a['knife_link']=='link_0' and any(a['hand_link'] in ['hand_r_'+d+'_link4','hand_r_'+d+'_pad_link'] for d in ['index','middle','ring']);r.append(min(0.,a['gap_lower_bound_m']+(.00035 if bearing else -.0003))*900)
  return r
 def residual(x):
  h=q0.copy();h[ids]=x;r=common(h)
  for n in names:
   P,_=surface(h,n);target=prior[n].copy();target[0 if n!=names[1] else 1]=-.0095 if n==names[0] else .0095 if n==names[2] else -.004;d=P-target;r.extend(d*np.array([700.,120.,90.]) if n!=names[1] else d*np.array([100.,700.,90.]));r.append(max(0.,abs(P[1])-.0038)*500 if n!=names[1] else max(0.,abs(P[0])-.0088)*500)
  r.extend((x-q0[ids])*.02);return np.asarray(r)
 start=time.time();fit=least_squares(residual,q0[ids],bounds=(g.w.lower[ids]+.04,g.w.upper[ids]-.04),max_nfev=65,diff_step=1e-5);q=q0.copy();q[ids]=fit.x;F=g.w.forward(q);floor=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,p in g.meshes.items() for v,_ in p);bad=check.inspect(q);contacts=[dict(link=n,point=surface(q,n)[0].tolist(),material=surface(q,n)[1].tolist(),inward_knife=dirs[n].tolist()) for n in names];errors={n:float(abs(surface(q,n)[0][0 if n!=names[1] else 1]-(-.0095 if n==names[0] else .0095 if n==names[2] else -.004))) for n in names};result=dict(candidate='D708',source=str(source),wrist_in_knife=L.tolist(),table_object_world=O.tolist(),table_yaw_degrees=c['table_yaw_degrees'],hand_q=q.tolist(),contacts=contacts,table_clearance_m=floor,self=bad,normal_surface_errors_m=errors,geometry_permits_native=not bad and floor>.0002 and max(errors.values())<.0006,elapsed_s=time.time()-start,scope=__doc__);(out/'candidate.json').write_text(json.dumps(result,indent=2))
 if not result['geometry_permits_native']:
  note('functional_side_pickup_geometry_blocked',[str(out/'candidate.json')],result,'Onlycurrentfloor/self/contactconstraintchanges next; no nativeknownblock');print(json.dumps({k:result[k] for k in ['geometry_permits_native','table_clearance_m','self','normal_surface_errors_m']}),flush=True);return
 # Open all carriers together so one digit cannot consume another's space.
 targets={c['link']:np.asarray(c['point'])-.003*dirs[c['link']] for c in contacts};opening_ids=np.r_[0:8,12:16]
 def opening(x):
  h=q.copy();h[opening_ids]=x;r=common(h)
  for n in names:r.extend((surface(h,n)[0]-targets[n])*500)
  r.extend((x-q[opening_ids])*.025);return np.asarray(r)
 fit=least_squares(opening,q[opening_ids],bounds=(g.w.lower[opening_ids]+.04,g.w.upper[opening_ids]-.04),max_nfev=55,diff_step=1e-5);openq=q.copy();openq[opening_ids]=fit.x;above=W.copy();above[2,3]+=.025;initial,ik=k.solve_near(above,np.asarray(c['arm_q']),max_step=1.,minimum_margin=.06);guard=[]
 for t in np.arange(3.,5.0001,1/30):
  u=smooth((t-3)/2);h=(1-u)*openq+u*q;goal=W.copy();goal[2,3]+=.02*(1-smooth(t-3));F=g.w.forward(h);height=min(float((v@(goal@F[n])[:3,:3].T+(goal@F[n])[:3,3])[:,2].min()-.75) for n,p in g.meshes.items() for v,_ in p);guard.append(dict(time_s=float(t),table_clearance_m=height,self=check.inspect(h)))
 summary=dict(min_table_clearance_m=min(r['table_clearance_m'] for r in guard),self_frames=sum(bool(r['self']) for r in guard),initial_arm_ik=ik,opening_errors_m={n:float(np.linalg.norm(surface(openq,n)[0]-targets[n])) for n in names});(out/'dense-approach-guard.json').write_text(json.dumps(dict(summary=summary,rows=guard),indent=2));eligible=summary['min_table_clearance_m']>.0001 and not summary['self_frames'] and ik['position_m']<.0005
 if eligible:
  physics=json.loads((B/'development/direct-forward-primary-rolling-patch-v704/simulation/physics.json').read_text());spec=dict(duration_s=9.,initial_arm_q=initial.tolist(),wrist_in_knife=L.tolist(),open_q=openq.tolist(),close_q=q.tolist(),pregrasp_clearance_m=.02,lift_m=.055,arm_command_margin_rad=.06,material_points={r['link']:r['material'] for r in contacts},grip_normal_reference_N={names[0]:.9,names[1]:.15,names[2]:.9},grip_force_directions_knife={n:d.tolist() for n,d in dirs.items()},grip_motor_margin_rad=.035,hand_kp=physics['kp'][7:],knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');prefix=dict(duration_s=9.,physical_initial_xy=O[:2,3].tolist(),physical_initial_yaw_deg=c['table_yaw_degrees'],physical_initial_object_world=O.tolist(),direct_pickup=spec,rows=[dict(time_s=0.,arm_q=initial.tolist(),hand_q=openq.tolist())],candidate='D708',grasp_geometry=str(out/'candidate.json'),lineage='707functional sidegeometry -> cleared708 -> pendingownfreshnative. Samewristoperationblocked; lateradjustmentmustconsumeownactualoutput.',goal8_status='Developmentpickup only; nocontinuousGoal orcapstrokeinheritance',scope=__doc__);(out/'prefix.json').write_text(json.dumps(prefix,indent=2))
 note('functional_side_pickup_motor_terminal',[str(out/'candidate.json'),str(out/'dense-approach-guard.json')],dict(geometry_permits_native=eligible,guard=summary,layout=cfg['support_layout']),'Clear -> fresh9s pickup, ownactualbearing thennecessarywrist/Thumbadaptation; blocked -> exactapproachconstraint')
 print(json.dumps(dict(geometry_permits_native=eligible,guard=summary)),flush=True)

if __name__=='__main__':main()
