"""Two-second no-policy grasp acceptance, registered before manipulation results."""
import argparse,json,hashlib,time
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
from scripts.prepare_wuji_geometry import meshes,penetration
from scripts.wuji_kinematics import WujiKinematics
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--split',default='screen-attempts');p.add_argument('--take',type=int,default=16);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--research-dir',type=Path,default=Path('research/real-knife-press-resistance-20261002'));p.add_argument('--sources',type=int,nargs='+',default=[0,3])
 a=p.parse_args()
 root=Path(__file__).resolve().parents[1];d=root/a.research_dir;meta=json.loads((d/'ASSETS.json').read_text())[a.label];path=d/'data'/a.label/(a.split+'.npy');states=np.load(path);n=len(states)//len(a.sources)
 a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
 hand=WujiKinematics();mesh=meshes(hand);size=np.array(meta['parameters']['handle_size']);origin=np.array(meta['parameters']['slider_origin']);base=np.array([.019,.008,.147]);origin0=np.array([0,.0055,.010624586881962734]);lineage=np.load(d/'data'/a.label/'adapted-seeds.npy')
 # Relative penetration allowance uses already validated original contact preload.
 original_seeds=np.load(root/'research/multigrasp-20260928/data/candidates.npy')[:4]
 base_depth=[penetration(hand,mesh,s,base,origin0) for s in original_seeds]
 depths=[penetration(hand,mesh,s,size,origin) for s in states]
 limit=np.r_[hand.lower,hand.lower];upper=np.r_[hand.upper,hand.upper]
 legal=np.isfinite(states).all(1)&(states[:,:40]>=limit-2e-6).all(1)&(states[:,:40]<=upper+2e-6).all(1)
 geo=np.array([depths[i]<=base_depth[a.sources[i//n]]+.001 for i in range(len(states))])
 overrides=['object='+meta['object'],'hand=wuji_paper_official_actuator','test=True','task.env.episodeLength=60']
 if meta['parameters']['round']!='geometry-generalization-20261002':overrides+=['+task.env.geometryRound='+meta['parameters']['round']]
 reach=np.ones(len(states),dtype=bool)
 if meta['parameters']['round']=='real-knife-press-resistance-20261002':
  grasp=json.loads((d/'GRASPS.json').read_text())[a.label]
  reach=np.asarray([grasp[a.sources[i//n]]['thumb_reach_valid'] for i in range(len(states))],dtype=bool)
 geo=geo&reach
 cfg=configuration('wuji_geometry',len(states),overrides,train='wujiAcquisitionSAPG',seed=2026100209)
 cfg.task.env.trainingStates=str(path.relative_to(root))
 (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True));env=make_env(cfg)
 assert bool(env.instance_grasp_state_pose_is_local.all()), 'New cache must use hand_base poses'
 frames=[]
 try:
  env.configure_fixed_grasp_consecutive_evaluation('000',states[0],goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=len(states));env.eval_grasp_states[:]=torch.as_tensor(states,device=env.device);env.success_hold_duration=1e9;env.eval_goal_timeout=0.
  original=env.compute_reward
  def capture(actions):
   active=env.eval_active_mask.clone();original(actions)
   angle=2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
   row=dict(active=active,drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1),rotation=angle,fall=env.debug_reset_cause_fall,invalid=env.debug_reset_cause_invalid,q=env.hand_dof_pos,target=env.cur_targets[:,:20],slider=env.obj_dof_pos[:,0],object_pos=env.object_pos,object_rot=env.object_rot,contact=env.contact_info)
   frames.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})
  env.compute_reward=capture;env.reset();zero=torch.zeros((len(states),20),device=env.device)
  for step in range(60):
   if env.is_grasp_evaluation_complete():break
   env.step(zero)
  trace={k:np.stack([f[k] for f in frames]) for k in frames[0]};np.savez_compressed(a.output/'trace.npz',**trace)
  alive=trace['active'].all(0)&~trace['fall'].any(0)&~trace['invalid'].any(0)
  stable=alive&(trace['drift']<.01).all(0)&(trace['rotation']<.25).all(0)&(len(frames)==60)
  assert max(abs(trace['target']-states[None,:,20:40]).ravel())<2e-6
  records=[];selected=[];sources=[]
  for block,source in enumerate(a.sources):
   ids=list(range(block*n,(block+1)*n));valid=[i for i in ids if legal[i] and geo[i] and stable[i]];chosen=valid[:a.take];selected+=chosen
   sources.append(dict(source=source,attempted=n,generated=int(legal[ids].sum()),geometry_accepted=int((legal&geo)[ids].sum()),static_valid=len(valid),selected=len(chosen),baseline_vertex_penetration_m=base_depth[source]))
   for i in ids:
    records.append(dict(row=i,source=source,legal=bool(legal[i]),geometry_valid=bool(geo[i]),static_stable=bool(stable[i]),valid=bool(legal[i]&geo[i]&stable[i]),vertex_penetration_m=depths[i],max_drift_m=float(trace['drift'][:,i].max()),max_rotation_rad=float(trace['rotation'][:,i].max()),support_contact_seen=bool(trace['contact'][:,i,1:].any()),thumb_contact_seen=bool(trace['contact'][:,i,0].any()),rejection=('joint/finite' if not legal[i] else 'penetration allowance' if not geo[i] else 'static drift/invalid/fall' if not stable[i] else None)))
  np.save(a.output/'valid-states.npy',states[selected]);(a.output/'selection.json').write_text(json.dumps(dict(selected_attempt_rows=selected,sources=sources,source_order=[a.sources[i//n] for i in selected],no_policy_filter=True),indent=2)+'\n')
  report=dict(label=a.label,split=a.split,thresholds=dict(duration_s=2,max_drift_m=.01,max_rotation_rad=.25,penetration='vertex SDF no more than source baseline +1mm; proxy, not exact hull penetration',reach='local IK preserves thumb working-region contact within2mm',finite_and_joint_limits=True),sources=sources,records=records,wall_seconds=time.monotonic()-started,initial_states_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),effective_randomize=bool(env.randomize),effective_force_scale=float(env.force_scale),effective_joint_noise=float(env.joint_noise),scope='Static holding and geometry proxy; not manipulation or hardware')
  (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(label=a.label,sources=sources,wall_seconds=report['wall_seconds'])),flush=True)
 finally:env.gym.destroy_sim(env.sim)
if __name__=='__main__':main()
