"""One actual takeover packet through n=1 and n=8 bridges, without rerunning physics.

Separates input/mapping/model errors from later closed-loop sensitivity. Small
floating-point differences do not establish a PhysX fault or robust behavior.
"""
from isaacgym import gymapi
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import torch
from scripts.wuji_goal_common import configuration
from scripts.g2_batched_r800 import BatchedG2R800
from scripts.wuji_robust_learning import TEACHER,R800,ResidualActorCritic
from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action

def main():
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);tr=np.load(a.trace);init=np.load(a.initial);torch.backends.cudnn.allow_tf32=False
 cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301);saved=torch.load(a.checkpoint,map_location='cuda');model=ResidualActorCritic(154,181).cuda();model.load_state_dict(saved['model']);model.eval();rows=[]
 for n in [1,8]:
  b=BatchedG2R800(cfg,TEACHER,R800,n);q=torch.tensor(tr['q'][480,0],device=b.device).repeat(n,1);issued=torch.tensor(tr['motor_target'][479,0],device=b.device).repeat(n,1);arm=torch.tensor(tr['arm_q'][479,0],device=b.device).repeat(n,1)
  qhist=torch.tensor(tr['q'][431:481,0],device=b.device);ahist=torch.tensor(tr['action'][430:480,0],device=b.device);b.history=torch.cat([b.normalized(qhist),ahist],-1)[None].repeat(n,1,1);b.history_count[:]=50;ids=torch.arange(n,device=b.device);obj=torch.tensor(init['cal_object'][0],device=b.device).repeat(n,1);slider=torch.tensor(init['cal_slider'][0],device=b.device).repeat(n,1);b.takeover(ids,q,issued,obj,slider)
  public=b.features(q,torch.full((n,),.04,device=b.device),arm,torch.ones(n,dtype=torch.bool,device=b.device))
  with torch.no_grad():mean=model.actor_logits(public)
  act=bounded_motor_residual_action(issued,b.known,mean,torch.tensor(saved['action_scale'],device=b.device));target=b.known.step(act)
  data=dict(encoded=b.last_encoder_input[0].cpu().numpy(),public=public[0].cpu().numpy(),raw_base=b.base_action[0].cpu().numpy(),residual=mean[0].cpu().numpy(),motor_target=target[0].cpu().numpy());np.savez_compressed(a.output/('packet-n%d.npz'%n),**data);rows.append(data)
 keys=['encoded','public','raw_base','residual','motor_target'];errors={k:float(abs(rows[0][k]-rows[1][k]).max()) for k in keys};legal=np.r_[np.arange(131),np.arange(151,154)];errors['measured_known_public']=float(abs(rows[0]['public'][legal]-rows[1]['public'][legal]).max());passed=errors['encoded']<2e-5 and errors['measured_known_public']<2e-5 and errors['motor_target']<2e-6
 result=dict(scope=__doc__,trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),actual_50_history_frames=True,errors=errors,interface_passed=passed,behavior_parity_passed=False,math_flags=dict(matmul_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_tf32=torch.backends.cudnn.allow_tf32),next='Training may address demonstrated contact sensitivity only after input/initialization checks; no exact behavior guarantee from packet parity')
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert passed,'Canonical packet mapping/motor parity failed'

if __name__=='__main__':main()
