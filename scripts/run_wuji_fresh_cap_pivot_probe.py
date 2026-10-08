"""Frozen fresh32-episode pivot mechanism test; no restored held-state init.

No training updates or capacity inheritance. Not a video/native acceptance.
"""
import argparse,json,hashlib,shutil
from pathlib import Path
import isaacgym
import torch,numpy as np
from scripts.wuji_fresh_prefix_learning import FreshPrefixRegrasp
from scripts.train_wuji_fresh_regrasp import FreshRegraspActor
from scripts.wuji_cap_contact_pivot import CapContactPivot
from scripts.wuji_fresh_capacity_probe import probe
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

def planned_pivot(pivot,q,O,slider):
 f=pivot.f;X=np.linalg.inv(O)@f.kin.forward(q[:7]);point=pivot.point(q[7:],X);seed=q[23:].copy();target3=max(q[25],pivot.g.w.lower[18]+.15)
 def residual(v):
  h=q[7:].copy();h[16:]=v;return np.r_[(pivot.point(h,X)-point)*1000,(v[2]-target3)*4,(v-seed)*.0001]
 fit=least_squares(residual,np.clip(seed,pivot.g.w.lower[16:]+1e-5,pivot.g.w.upper[16:]-1e-5),bounds=(pivot.g.w.lower[16:]+1e-5,pivot.g.w.upper[16:]-1e-5),max_nfev=100,diff_step=1e-5);qq=q.copy();qq[23:]=fit.x;arm=q[:7].copy();path=[];problem=None
 for angle in np.linspace(0,20,21):
  R=Rotation.from_rotvec([0,np.deg2rad(angle),0]).as_matrix();Y=X.copy();Y[:3,:3]=R@X[:3,:3];Y[:3,3]=point+R@(X[:3,3]-point);arm,ik=f.kin.solve_near(O@Y,arm,max_step=.08,minimum_margin=.01);qq[:7]=arm
  if ik['position_m']>.0002 or ik['rotation_rad']>.002:problem='Arm pivot unreachable';break
  if f.H.inspect(qq[7:]):problem='Planned hand intersection';break
  for digit in ['index','middle','ring','pinky','thumb']:
   before=f.g.gaps(q[7:],X,slider,digit);after=f.g.gaps(qq[7:],Y,slider,digit)
   if any(b['gap_lower_bound_m']<min(-.0002,a['gap_lower_bound_m']-.0002)for a,b in zip(before,after)):problem='New knife collision '+digit;break
  path.append(dict(angle_deg=float(angle),q=qq.tolist(),ik=ik))
  if problem:break
 af=f.assess(qq,O,slider,full_path=problem is None);return dict(eligible=problem is None and af['reference_eligible'],failure=problem,affordance=af,path=path)

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--env',type=int,default=15);p.add_argument('--frames',type=int,default=345);p.add_argument('--state-triggered',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(20261008801);saved=torch.load(a.source/'policy-before-update.pth',map_location='cpu');cfg=saved['config'];noise=np.load(a.source/'actual-regrasp-traces.npz')['action_noise'];keys=['n','source','reference','prefix_trace','prefix_spec','functional_workspace','linear_potential','failure_penalty','self_bad_penalty','task_geometry','free_motor','workspace_query_distance_m','workspace_cadence_frames','pose_motion_observation','fail_on_self_contact','functional_contact_reward'];envcfg={k:cfg[k]for k in keys if k in cfg};proof=dict(source=str(a.source),chosen_env=a.env,NN_frames=a.frames,state_triggered=a.state_triggered,config=envcfg,checkpoint_sha256=hashlib.sha256((a.source/'policy-before-update.pth').read_bytes()).hexdigest(),question='Does coordinated20degreecontactpivot physicallyretainload and make originalB available fromactualroofcontact? Yes: independentvideo/fullfreshrobustness; no: changebearing/mechanism, no pressuregrid.',scope=__doc__);runtime=a.output/'controller-source';runtime.mkdir()
 for name in ['run_wuji_fresh_cap_pivot_probe.py','wuji_cap_contact_pivot.py','wuji_fresh_prefix_learning.py','wuji_fresh_capacity_probe.py','wuji_retained_push_skill.py','wuji_functional_entry_affordance.py']:
  shutil.copyfile(Path('scripts')/name,runtime/name)
 (a.output/'config.json').write_text(json.dumps(proof,indent=2));record('frozen_fresh_cap_contact_pivot_mechanism_started',[str(a.output/'config.json')],proof,updates={'add_active_jobs':[str(a.output)]},next_step='Firstactualpivot andoriginalcompleteB result, no parentcapacityclaim')
 e=None;states=[];capacity=None;reason=None;nnstates=[];predictions=[];chosen=None;trigger_frame=None
 try:
  e=FreshPrefixRegrasp(**envcfg);model=FreshRegraspActor(168,27).cuda();model.load_state_dict(saved['model']);model.eval();obs=e.observation();period=cfg['action_period_frames'];dwell=torch.zeros(e.n,device=e.device);pivot=CapContactPivot(e.cfg,dict(start_s=0.,end_s=6.,angle_deg=20.,thumb_joint3_reserve_rad=.15,entry_tail_distance_m=.003),a.output)
  for frame in range(a.frames):
   if frame%period==0:
    with torch.no_grad():mean=model(obs)[0].mean
    action=mean+e.tensor(noise[frame//period])
   obs,reward,done,info=e.step(action)
   if a.state_triggered:
    nnstates.append((e.dof.clone(),e.command_target.clone(),e.rb[:,e.object_index].clone(),e.contact.clone()))
    ready=info['held']&(info['tail_roof_distance_m']<.0015)&(info['cap_distance_m']<.0015)&(info['linear_speed_m_s']<.08)&(info['angular_speed_rad_s']<.8)&(info['slider_drift_m']<.002);dwell=torch.where(ready,dwell+1,torch.zeros_like(dwell))
    for candidate in torch.nonzero(dwell==3).flatten().cpu().tolist():
     q=e.dof[candidate,:27,0].cpu().numpy().astype(float);o=e.rb[candidate,e.object_index].cpu().numpy();prediction=planned_pivot(pivot,q,transform(o[:3],o[3:7]),float(e.dof[candidate,27,0]));predictions.append(dict(env=candidate,frame=frame,prediction=prediction))
     if prediction['eligible']:chosen=candidate;trigger_frame=frame;break
    if chosen is not None:break
    if e.failed.all():break
   else:
    states.append((e.dof[a.env].clone(),e.command_target[a.env].clone(),e.rb[a.env,e.object_index].clone(),e.contact[a.env].clone(),'NN'))
    if bool(e.failed[a.env]):raise ValueError('Selectedfrozenfresh episode failedbeforepivot atframe '+str(frame))
  if a.state_triggered:
   (a.output/'actual-pivot-predictions.json').write_text(json.dumps(predictions,indent=2))
   if chosen is None:raise ValueError('No actuallyheld settledclosed roof entry with plannedpivotworkspace in frozen32 physicalepisodes')
   a.env=chosen;states=[(s[0][chosen],s[1][chosen],s[2][chosen],s[3][chosen],'NN')for s in nnstates];print(json.dumps(dict(chosen=chosen,trigger_frame=trigger_frame)),flush=True)
  motors=e.command_target.clone()
  for frame in range(180):
   q=e.dof[a.env,:27,0].cpu().numpy();o=e.rb[a.env,e.object_index].cpu().numpy();issued=e.command_target[a.env].cpu().numpy();slider=float(e.dof[a.env,27,0]);arm,hand=pivot.command(frame/30,transform(o[:3],o[3:7]),q,issued,slider);motors[a.env]=e.tensor(np.r_[arm,hand]);e.servo(motors);states.append((e.dof[a.env].clone(),e.command_target[a.env].clone(),e.rb[a.env,e.object_index].clone(),e.contact[a.env].clone(),'pivot'))
   if float(e.whole_clearance()[a.env])<.025:raise ValueError('Lost usefulcarrying duringcap pivot frame '+str(frame))
  q=e.dof[a.env,:27,0].cpu().numpy().astype(float);o=e.rb[a.env,e.object_index].cpu().numpy();af=e.affordance.assess(q,transform(o[:3],o[3:7]),float(e.dof[a.env,27,0]));(a.output/'actual-pivot-entry.json').write_text(json.dumps(af,indent=2))
  if not af['reference_eligible']:raise ValueError('Actualpivot full30 workspace/self rejects originalB: '+str(af))
  capacity=probe(e,a.env,a.output/'fullB')
 except (RuntimeError,ValueError) as exc:reason=type(exc).__name__+': '+str(exc)
 finally:
  if states:np.savez_compressed(a.output/'actual-frozen-NN-pivot-trace.npz',dof=torch.stack([x[0]for x in states]).cpu().numpy(),issued=torch.stack([x[1]for x in states]).cpu().numpy(),object=torch.stack([x[2]for x in states]).cpu().numpy(),normal_contact=torch.stack([x[3]for x in states]).cpu().numpy(),phase=np.array([x[4]for x in states]),prefix_q_1hz=e.prefix_actual_q_1hz[:,a.env].cpu().numpy(),prefix_object_1hz=e.prefix_actual_object_1hz[:,a.env].cpu().numpy())
  if e:e.close()
  result=dict(capacity=capacity,failure=reason,frames=len(states),chosen_env=chosen,trigger_frame=trigger_frame,predictions=len(predictions),scope=__doc__);(a.output/'result.json').write_text(json.dumps(result,indent=2));record('frozen_fresh_cap_contact_pivot_mechanism_terminal',[str(a.output/'result.json')],result,updates={'remove_active_jobs':[str(a.output)]},next_step='ActualB capacityandbearingdecides; ifpass independentvideo+nativeapproachrobustness, iffailurechangecontactmechanism');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
