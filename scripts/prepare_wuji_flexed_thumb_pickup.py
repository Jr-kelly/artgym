"""New pad-opposed pickup from an actual tabletop initialization, motors only."""
import argparse,json,sys,shutil,subprocess,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--open-audit',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);c=json.loads(a.geometry.read_text());assert c['geometry_permits_native'];f=FunctionalEntryAffordance();g=f.g;L=np.array(c['wrist_in_knife']);closed=np.array(c['hand_q']);ids=np.array(list(range(8))+list(range(16,20)));names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_pad_link'];verts={n:np.concatenate([v for v,_ in g.meshes[n]])for n in names};signs=[-1.,-1.,1.]
 def surfaces(h):
  F=g.w.forward(h);pts=[];materials=[]
  for name,sgn in zip(names,signs):
   T=L@F[name];P=verts[name]@T[:3,:3].T+T[:3,3];depth=sgn*P[:,0];weights=np.exp((depth-depth.max())/.0002);weights/=weights.sum();pts.append(weights@P);materials.append(weights@verts[name])
  return np.array(pts),materials,F
 base=json.loads(Path('runs/flat-table-20261006/direct/preparation/current-C560-fresh-no-extra-ring-v743/prefix.json').read_text());O=np.array(base['physical_initial_object_world']);W=O@L;target,materials,F=surfaces(closed);target[:,0]+=np.array([.003,.003,-.003]);seed=closed[ids].copy();lo=g.w.lower[ids]+.035;hi=g.w.upper[ids]-.035;lo[10]=.1
 record('flexed_thumb_open_and_pickup_preparation_started_v865',[str(a.geometry)],dict(question='Can newpad-sidegrip open3mm withouttable/self interference, thennaturallycarry underoriginalnormalreferences? Yes: itsownflip/B; no: exactinitialcontactmechanismfailure, noforceincrease.',scope=__doc__),next_step='Oneopen solve; actualfresh10s acquisition/lift, no recordedheld-state init')
 def residual(v):
  h=closed.copy();h[ids]=v;points,_,F=surfaces(h);r=list(((points-target)*700).flatten());r.extend((v-seed)*.02)
  for name,parts in g.meshes.items():
   T=W@F[name]
   for vv,_ in parts:r.append(min(0.,float((vv@T[:3,:3].T+T[:3,3])[:,2].min()-.7503))*1400)
  for digit in ['index','middle','ring','pinky','thumb']:r.extend(min(0.,x['gap_lower_bound_m']-.0005)*900 for x in g.gaps(h,L,0.,digit,frames=F))
  r.extend(min(0.,x['gap_lower_bound_m']-.0002)*900 for x in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));return np.array(r)
 if a.open_audit:opened=np.array(json.loads(a.open_audit.read_text())['open_hand_q'])
 else:
  fit=least_squares(residual,seed,bounds=(lo,hi),max_nfev=60,diff_step=1e-5);opened=closed.copy();opened[ids]=fit.x
 points,_,F=surfaces(opened);floor=min(float((vv@(W@F[name])[:3,:3].T+(W@F[name])[:3,3])[:,2].min()-.75)for name,parts in g.meshes.items()for vv,_ in parts);H=f.H.inspect(opened);errors=np.linalg.norm(points-target,axis=1);audit=dict(open_hand_q=opened.tolist(),open_contact_points=points.tolist(),open_target_points=target.tolist(),open_error_m=errors.tolist(),table_clearance_m=floor,self=H,reused_open_audit=str(a.open_audit)if a.open_audit else None);(a.output/'open-audit.json').write_text(json.dumps(audit,indent=2));assert floor>.00015 and not H and errors.max()<.0008,audit
 kp=np.array(base['direct_pickup']['hand_kp']);motor=closed.copy();preloads=[]
 for digit,name,m,sgn,normal in zip(['index','middle','thumb'],names,materials,signs,[.7,.7,1.4]):
  ji=np.array(list(range(4))if digit=='index'else list(range(4,8))if digit=='middle'else list(range(16,20)));J=np.empty((3,4))
  def point(h):
   T=L@g.w.forward(h)[name];return T[:3,:3]@m+T[:3,3]
  for j,index in enumerate(ji):
   plus=closed.copy();minus=closed.copy();plus[index]+=1e-5;minus[index]-=1e-5;J[:,j]=(point(plus)-point(minus))/2e-5
  # Same original reference .7/.7/1.4N and finite motorPD; not force guarantee.
  preload=J.T@np.array([sgn*normal,0.,0.])/kp[ji];motor[ji]+=np.clip(preload,-.12,.12);preloads.append(dict(digit=digit,normal_proxy_reference_N=normal,inward_direction_knife=[sgn,0.,0.],preload_rad=preload.tolist()))
 motor=np.clip(motor,g.w.lower,g.w.upper);s=base['direct_pickup'];s.update(wrist_in_knife=L.tolist(),open_q=opened.tolist(),close_q=motor.tolist(),material_points={n:m.tolist()for n,m in zip(names,materials)},grip_force_directions_knife={n:([sgn,0.,0.])for n,sgn in zip(names,signs)})
 s.pop('loading_motor_prior',None);s.pop('loading_motor_prior_until_s',None);above=W.copy();above[2,3]+=.1;arm,ik=f.kin.solve_near(above,np.array(s['initial_arm_q']),max_step=.6,minimum_margin=.035);assert ik['position_m']<.0005 and ik['rotation_rad']<.003,ik;s['initial_arm_q']=arm.tolist();first=s['continuous_stages'][0]
 # Captured pad-opposed targets must not pass through old thumb-heel tracking.
 # Keep only finite motor rows; world translation and live_hand override them.
 inherited=json.loads(Path(first['motor']).read_text())
 plain={k:v for k,v in inherited.items() if k in ['rows','required_actual_source']}
 plain['scope']='Rows only interface prior; live acquired wrist/issued hand govern lift. No inherited contact follower.'
 lift_prior=a.output/'acquired-lift-motor-prior.json';lift_prior.write_text(json.dumps(plain,indent=2))
 first.update(motor=str(lift_prior),hold_acquired_hand_targets=True,world_translation_m=[0,0,.09]);s['continuous_stages']=[first];base['duration_s']=10.;base['rows']=[dict(time_s=0.,arm_q=arm.tolist(),hand_q=opened.tolist())];base['scope']=__doc__+' Geometry plannedinitialgrip and finitepreload; Bgoal original773 unchanged. Physicalnewpickup mustbeverified.';(a.output/'prefix.json').write_text(json.dumps(base,indent=2));(a.output/'preload.json').write_text(json.dumps(dict(preloads=preloads,closed_motor=motor.tolist(),actual_geometry_q=closed.tolist(),above_IK=ik),indent=2));cmd=json.loads(Path('runs/flat-table-20261006/direct/development/current-C560-fresh-no-extra-ring-v743/command.json').read_text());cmd[0]=sys.executable
 for flag,value in [('--flat-table-prefix',str(a.output/'prefix.json')),('--output',str(a.output/'simulation')),('--seconds','.03333333333333333')]:cmd[cmd.index(flag)+1]=value
 cmd+=['--support-camera-direction','-.6','.4','.3'];(a.output/'command.json').write_text(json.dumps(cmd,indent=2));runtime=a.output/'controller-source';runtime.mkdir()
 for name in ['prepare_wuji_flexed_thumb_pickup.py','plan_wuji_flexed_thumb_table_pinch.py','run_g2_flat_table_demo.py','wuji_direct_pickup.py','wuji_direct_route.py']:shutil.copyfile(Path('scripts')/name,runtime/name)
 record('flexed_thumb_actual_fresh_pickup_started_v865',[str(a.output/'command.json'),str(a.output/'preload.json')],dict(open_audit=audit,preloads=preloads,scope=base['scope']),updates={'add_active_jobs':[str(a.output)]},next_step='Actualflat10s pickup/lift determinesnext. No idealheldstate/oldtuple/preloadmaximum/refgoalchange')
 try:subprocess.run(cmd,check=True)
 finally:record('flexed_thumb_actual_fresh_pickup_terminal_v865',[str(a.output/'simulation')],updates={'remove_active_jobs':[str(a.output)]},next_step='Actualbearing/height/H and contactplacement decideownflip/B connection, no pressuregrid')
if __name__=='__main__':main()
