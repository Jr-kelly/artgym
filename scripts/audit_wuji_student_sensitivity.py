"""CPU counterfactual latent/target gradient diagnostics on frozen teacher histories."""
import argparse,hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration
import torch
from omegaconf import OmegaConf
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.utils.distill_action_loss import frozen_actor_mean
from scripts.wuji_student_interface import build_encoder,legal_policy_observation
from scripts.wuji_kinematics import WujiKinematics
from isaacgymenvs.utils.torch_jit_utils import scale,unscale

def main():
 p=argparse.ArgumentParser();p.add_argument('--student',type=Path,required=True);p.add_argument('--teacher',type=Path,required=True);p.add_argument('--probes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 torch.set_num_threads(2)
 cfg=configuration('wuji_multigrasp',1,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','rl_device=cpu','sim_device=cpu'],train='wujiAcquisitionSAPG',seed=2026093031)
 config=preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True));player=build_policy_player(cfg,config,a.teacher,_infer_expl_num_blocks(a.teacher),0)
 for v in player.model.parameters():v.requires_grad_(False)
 artifact=torch.load(a.student,map_location='cpu');encoder=build_encoder(artifact['kind']).eval();encoder.load_state_dict(artifact['student_encoder'])
 assert artifact['kind']=='S0', 'This diagnostic uses the unextended S0 parent'
 probes=torch.load(a.probes,map_location='cpu');rows=[]
 hand=WujiKinematics();lower=torch.tensor(hand.lower,dtype=torch.float32);upper=torch.tensor(hand.upper,dtype=torch.float32)
 teacher_calls=[0]
 def counted(*unused):teacher_calls[0]+=1
 hook=player.model.a2c_network.priv_encoder.register_forward_hook(counted)
 for time_index in [3,12,24]:
  q=probes[time_index];ids=torch.arange(0,len(q['x']),4);source=ids//(len(q['x'])//4)
  obs=legal_policy_observation(q['obs'][ids]);incoming=[s[:,ids,:].clone() for s in q['rnn']]
  with torch.no_grad():pred=encoder(q['x'][ids]);label=q['label'][ids];teacher=frozen_actor_mean(player,obs,label,incoming).clamp(-1,1)
  latent=pred.detach().requires_grad_(True);mu=frozen_actor_mean(player,obs,latent,incoming)
  # Forward error uses clipped executed actions and exact per-joint control
  # spans. STE supplies a nonzero surrogate gradient in saturated output regions.
  action=mu+(mu.clamp(-1,1)-mu).detach();span=torch.tensor([.04]*16+[.025]*4)
  def targets(act,surrogate=False):
   target=q['initial'][ids]+.04*act
   target[:,16:]=q['previous'][ids,16:]+.025*act[:,16:]
   bounded=torch.maximum(torch.minimum(target,upper),lower)
   bounded=scale(unscale(bounded,lower,upper),lower,upper)
   bounded=torch.maximum(torch.minimum(bounded,upper),lower)
   return target+(bounded-target).detach() if surrogate else bounded
  target_error=(targets(action,True)-targets(teacher)).square().mean(1)
  grad_target=torch.autograd.grad(target_error.sum(),latent)[0]
  grad_latent=2*(pred-label)/pred.shape[1]
  cosine=torch.nn.functional.cosine_similarity(grad_target,grad_latent,dim=1)
  for s in range(4):
   sel=source==s
   rows.append(dict(probe_step=q['step'],source=s,n=int(sel.sum()),latent_mse=float((pred[sel]-label[sel]).square().mean()),executed_target_mse_rad2=float(target_error[sel].mean()),gradient_cosine_mean=float(cosine[sel].mean()),negative_gradient_alignment=int((cosine[sel]<0).sum()),mean_norm_latent_gradient=float(grad_latent[sel].norm(dim=1).mean()),mean_norm_target_gradient=float(grad_target[sel].norm(dim=1).mean()),saturated_actions=int((mu[sel].abs()>1).sum())))
 result=dict(student_sha256=hashlib.sha256(a.student.read_bytes()).hexdigest(),rows=rows,scope='Frozen teacher-history CPU diagnostic; joint-limited targets with original scale roundtrip and STE gradient; not live closedloop or proof of action-aware improvement',incoming_rnn='same detached incoming actor/critic states in both counterfactuals',actor_teacher_encoder_calls=teacher_calls[0])
 assert teacher_calls[0]==0;hook.remove()
 a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
