"""Masked controller extension must preserve the original optimization problem."""
import argparse,copy,json
from pathlib import Path
import isaacgym
import torch
from torch.nn import functional as F
from scripts.wuji_student_interface import build_encoder

def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',default='runs/unified-student-20261001/S0-3200/step_000800.pth');p.add_argument('--output',default='research/unified-student-20261001/controller-transplant-audit.json');args=p.parse_args()
 torch.set_num_threads(2)
 parent=torch.load(args.parent,map_location='cpu')
 probes=torch.load('runs/unified-student-20261001/teacher-legal-S2/latent-probes.pth',map_location='cpu')
 old=build_encoder('S0').eval();old.load_state_dict(parent['student_encoder'])
 new=build_encoder('SC').eval();state=copy.deepcopy(parent['student_encoder']);state['init_encoder.0.weight']=F.pad(state['init_encoder.0.weight'],(0,21));new.load_state_dict(state)
 op=torch.optim.Adam(old.parameters());op.load_state_dict(copy.deepcopy(parent['optimizer']))
 np=torch.optim.Adam(new.parameters());os=copy.deepcopy(parent['optimizer'])
 idx=[k for k,_ in new.named_parameters()].index('init_encoder.0.weight');pid=os['param_groups'][0]['params'][idx]
 for k in ['exp_avg','exp_avg_sq']:os['state'][pid][k]=F.pad(os['state'][pid][k],(0,21))
 np.load_state_dict(os)
 x=probes[3]['x'][::8];y=probes[3]['label'][::8];expanded=F.pad(x,(0,21))
 a=old(x);b=new(expanded);start=float((a-b).abs().max());assert start<1e-6
 for model,opt,data in [(old,op,x),(new,np,expanded)]:
  opt.zero_grad();loss=F.mse_loss(model(data),y);loss.backward();opt.step()
 maximum=0.
 for key,value in old.state_dict().items():
  other=new.state_dict()[key]
  if key=='init_encoder.0.weight':other=other[:,:55]
  maximum=max(maximum,float((value-other).abs().max()))
 assert maximum<1e-6 and torch.count_nonzero(new.init_encoder[0].weight[:,55:])==0
 r=dict(initial_prediction_max_difference=start,next_Adam_update_max_parameter_difference=maximum,tolerance=1e-6,old_and_new_optimizer_steps=parent['optimizer_steps']+1,masked_columns_remain_zero=True,scope='CPU controlled comparison of same actual pre-action history and teacher labels; no physics/data feedback')
 Path(args.output).write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
