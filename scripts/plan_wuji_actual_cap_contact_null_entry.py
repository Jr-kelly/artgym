"""Original30mm workspace relief with actual ThumbLink4 cap contact retained.

Fixed actual wrist and Index bearing; previously unloaded Middle may clear itself.
Small thumb null motion relieves the original reference's joint2/joint4 upper
endstops. Geometry and measured-normal torque transport are development proxies,
not physical load proof. No gain/force scan, new finger servo or physical setter.
"""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--surface-rolling',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.loads((a.source/'manifest.json').read_text());trace=np.load(meta['source']);source_clock=float(trace['time'][meta['takeover_index']]);logs=[json.loads(x)for x in (Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];C=min(logs,key=lambda r:abs(r['time_s']-source_clock))['contacts'];contacts=[c for c in C if c['hand_link']=='hand_r_thumb_link4'and c['knife_link']=='link_1'];assert contacts;assert not any('middle'in c['hand_link']for c in C);weights=np.array([c['normal_magnitude_N']for c in contacts]);weights/=weights.sum();material=weights@np.array([c['position_hand_link_m']for c in contacts]);Fnormal=sum((np.array(c['force_normal_contribution_knife_N'])for c in contacts),np.zeros(3));f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 h0=z['robot_q'][7:].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);ids=np.r_[np.arange(4,8),np.arange(16,20)];name='hand_r_thumb_link4';clock=time.monotonic();rows=[];failure=None;seed=h0[ids].copy();depth={}
 for d in ['middle','thumb']:
  for c in g.gaps(h0,L,float(z['slider_q']),d):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.00001)
 def decode(x):h=h0.copy();h[ids]=x;return h
 def point(h):
  T=L@g.w.forward(h)[name];return T[:3,:3]@material+T[:3,3]
 origin=point(h0);record('actual_cap_contact_null_30mm_workspace_started_v933',[str(a.source)],dict(scope=__doc__,material_point_link_m=material.tolist(),contact_point_knife_m=origin.tolist(),measured_normal_only_N=Fnormal.tolist(),source_clock_s=source_clock,thumb_joint4_initial=float(h0[19]),target_joint4=.63 if a.surface_rolling else .40,surface_rolling=a.surface_rolling),next_step='Localnullspace actualcap+Indexbearing, original30 workspace/H then one shortphysicalhold adjustment; no strokegaingrid')
 for index,target in enumerate(np.linspace(h0[19],.63,22) if a.surface_rolling else np.linspace(h0[19],.40,15)):
  previous=seed.copy()
  def residual(x):
   if time.monotonic()-clock>180:raise TimeoutError('Bounded actualcap localnull geometry')
   h=decode(x);F=g.w.forward(h);r=list((point(h)-origin)*(np.array([200.,2000.,200.])if a.surface_rolling else 1200));r.append((h[19]-target)*12);r.extend((x-previous)*.003)
   for fraction in [1.,.5]:
    mh=decode(previous*(1-fraction)+x*fraction);mf=F if fraction==1 else g.w.forward(mh);r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-(max(depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))],-.0001)if a.surface_rolling and c['hand_link']==name and c['knife_link']=='link_0'else depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]))*4000 for d in ['thumb','middle']for c in g.gaps(mh,L,float(z['slider_q']),d,frames=mf,certify_clearance_m=.0002))
   return np.array(r)
  try:seed=previous if index==0 else least_squares(residual,previous,bounds=(g.w.lower[ids]+.002,g.w.upper[ids]-.002),max_nfev=45,diff_step=1e-5).x
  except TimeoutError as e:failure=str(e);break
  h=decode(seed);bad=f.H.inspect(h);error=float(np.linalg.norm(point(h)-origin));workspace=f.assess_relative(L,h,float(z['slider_q']));margin=None
  if workspace['reference_eligible']:
   margin=FunctionalEntryAffordance(task_stroke_m=.033).assess_relative(L,h,float(z['slider_q']))
  row=dict(index=index,hand_q=h.tolist(),wrist_in_knife=L.tolist(),arm_q=z['robot_q'][:7].tolist(),contact_error_m=error,thumb_joint4_target=float(target),self=bad,workspace30=workspace,workspace33=margin);rows.append(row);print(json.dumps(row),flush=True)
  if error>(.001 if a.surface_rolling else .0002) or bad or abs(h[19]-target)>.02:failure='Original contact/self constraint blocked localnull path';break
  if(a.surface_rolling and workspace['reference_eligible'])or(margin and margin['reference_eligible']):break
 out=dict(source=str(a.source),rows=rows,failure=failure,geometry_pass=bool(rows and failure is None and rows[-1]['workspace30']['reference_eligible']),contact_link=name,material_point_link_m=material.tolist(),measured_contact_normal_only_knife_N=Fnormal.tolist(),moving_joint_indices=ids.tolist(),elapsed_s=time.monotonic()-clock,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_text(Path(__file__).read_text());record('actual_cap_contact_null_30mm_workspace_terminal_v933',[str(a.output/'result.json')],dict(passed=out['geometry_pass'],poses=len(rows),failure=failure,last=rows[-1]if rows else None),next_step='Only if original30 workspace improves andcontact/H kept ->native shortcontrolledentry change; thenoriginalB30; otherwise distinctlocalcontactmigration, no pressure/strokegrid')
if __name__=='__main__':main()
