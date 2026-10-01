"""CPU reset/step parity with original player, history update and controller methods."""
import argparse,hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.deploy.wuji.temporal_policy_runtime import WujiTemporalPolicyRuntime
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from isaacgymenvs.tasks.wuji_geometry import WujiGeometry
from isaacgymenvs.tasks.artmanip import ArtManip
from isaacgymenvs.utils.torch_jit_utils import unscale
from scripts.wuji_student_interface import build_encoder,install_student_player
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
class NoHardwareGym:
 def set_dof_position_target_tensor(self,*args):pass
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();torch.set_num_threads(2)
 root=Path(__file__).resolve().parents[1];d=root/'research/geometry-generalization-20261002';teacher=root/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth';student=root/'runs/unified-student-20261001/SA-real-51200/step_051200.pth'
 cfg=configuration('wuji_multigrasp',4,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','rl_device=cpu','sim_device=cpu'],train='wujiAcquisitionSAPG',seed=2026100211)
 runtime=WujiTemporalPolicyRuntime(cfg,teacher,student,n=4)
 ref=build_policy_player(cfg,preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),teacher,_infer_expl_num_blocks(teacher),0)
 artifact=torch.load(student,map_location='cpu');encoder=build_encoder('SC');encoder.load_state_dict(artifact['student_encoder']);ref.model.a2c_network.priv_encoder=encoder.eval();ref.model.eval();install_student_player(ref);init_player_rnn_for_batch(ref,4)
 proxy=WujiGeometry.__new__(WujiGeometry);proxy.device=torch.device('cpu');proxy.num_environments=4;proxy.proprio_history_len=50;proxy.num_hand_dofs=20;proxy.obj_dof_pos=torch.zeros((4,1));proxy.init_targets=torch.zeros((4,21));proxy.prev_targets=torch.zeros((4,21));proxy.cur_targets=torch.zeros((4,21));proxy.actions=torch.zeros((4,20));proxy.hand_dof_lower_limits=runtime.lower;proxy.hand_dof_upper_limits=runtime.upper;proxy.actuated_dof_indices=list(range(20));proxy.use_relative_control=False;proxy.act_moving_average=1.;proxy.force_scale=0.;proxy.object_is_lighter=False;proxy.gym=NoHardwareGym();proxy.sim=None;proxy.cfg={'env':{'supportActionSpan':.04,'thumbActionStep':.025}}
 initial=torch.zeros((4,55));history=torch.zeros((4,50,40));just_reset=torch.ones(4,dtype=torch.bool);qbase=torch.zeros((4,20));hashes={};errors=dict(public=0.,history=0.,action=0.,target=0.,rnn=0.);partial=[]
 def reset(label,ids):
  states=torch.from_numpy(np.load(d/'data'/label/'adapted-seeds.npy')[ids]);params=json.loads((d/'ASSETS.json').read_text())[label]['parameters'];bb0=torch.tensor(params['handle_size']).repeat(len(ids),1);bb1=torch.tensor(params['slider_size']).repeat(len(ids),1)
  untouched=[s[:,[i for i in range(4) if i not in ids]].clone() for s in runtime.player.states]
  runtime.reset(states[:,:20],states[:,40:47],states[:,47:54],bb0,bb1,states[:,20:40],ids=ids)
  assert all(torch.equal(x,s[:,[i for i in range(4) if i not in ids]]) for x,s in zip(untouched,runtime.player.states))
  raw=torch.cat([unscale(states[:,:20],runtime.lower,runtime.upper),states[:,40:54],states[:,55:70],bb0,bb1],-1);public=torch.cat([raw,raw.new_zeros((len(ids),56))],-1);pub,priv=original_to_acquisition_observations(public,raw.new_zeros((len(ids),21)));pub,_=align_quaternion_hemisphere(pub,priv,runtime.hemisphere_reference);initial[ids]=pub[:,:55]
  current=torch.cat([unscale(states[:,:20],runtime.lower,runtime.upper),states.new_zeros((len(ids),20))],-1);ArtManip._update_history_buf(proxy,history,current,env_ids=ids,step_update=False)
  for target in [proxy.init_targets,proxy.prev_targets,proxy.cur_targets]:target[ids,:20]=states[:,20:40]
  proxy.actions[ids]=0;qbase[ids]=states[:,:20];just_reset[ids]=True
  for s in ref.states:s[:,ids]=0
  hashes[label]=hashlib.sha256((d/'data'/label/'adapted-seeds.npy').read_bytes()).hexdigest()
 reset('baseline',[0,1,2,3])
 for step in range(80):
  if step in [17,41]:
   ids=[1,3] if step==17 else [0,2];reset('T90' if step==17 else 'W120',ids);partial.append(dict(step=step,ids=ids,untouched_rnn_exact=True))
  q=torch.maximum(torch.minimum(qbase+torch.sin(torch.arange(20)[None]*.4+step*.3)*.008,runtime.upper),runtime.lower);q[just_reset]=qbase[just_reset];goal=torch.full((4,1),.04 if (step//12)%2==0 else 0.)
  output=runtime.step(q,goal,applied_previous_action=proxy.actions,issued_previous_targets=proxy.prev_targets[:,:20]);current=torch.cat([unscale(q,runtime.lower,runtime.upper),proxy.actions],-1);ids=(~just_reset).nonzero(as_tuple=False).flatten();ArtManip._update_history_buf(proxy,history,current[ids],env_ids=ids,step_update=True)
  tips=runtime.fk(q);tips[just_reset]=initial[just_reset,34:49];public=torch.cat([initial,current,goal,tips],-1);x=torch.cat([history.flatten(1),initial,unscale(proxy.prev_targets[:,:20],runtime.lower,runtime.upper),goal/.04],-1)
  obs=torch.cat([public,torch.linspace(-100,100,26).repeat(4,1),torch.full((4,1),50.)],-1);ref.model.a2c_network.actor_encoder_obs_override=x
  with torch.no_grad():action=ref.get_action(obs,is_deterministic=True)
  proxy.pre_physics_step(action)
  for key,value in [('public',(output['public_observation']-public).abs().max()),('history',(output['student_observation']-x).abs().max()),('action',(output['action']-action).abs().max()),('target',(output['joint_targets']-proxy.cur_targets[:,:20]).abs().max()),('rnn',max((a-b).abs().max() for a,b in zip(output['rnn_states'],ref.states)))]:errors[key]=max(errors[key],float(value))
  just_reset[:]=False
 assert errors['public']<2e-6 and errors['history']<2e-5 and errors['action']<2e-4 and errors['target']<2e-5 and errors['rnn']<2e-4,errors
 result=dict(passed=True,steps=80,batch=4,dimensions=['baseline','T90','W120'],nonconstant_joint_inputs=True,partial_resets=partial,max_absolute_errors=errors,reference='Original build_policy_player/get_action + ArtManip history update + inherited WujiDemoAligned/ArtManip pre_physics_step with no-hardware output stub',models=dict(teacher=hashlib.sha256(teacher.read_bytes()).hexdigest(),student=hashlib.sha256(student.read_bytes()).hexdigest()),initial_data_sha256=hashes,scope='CPU legal input replay/parity, not physical rollout or hardware. Commands external. Runtime accepts initial calibration and known geometry; no current object/slider/contact truth.')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
