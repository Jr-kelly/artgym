"""Replay recorded legal H200 inputs on the independent CPU reset/step interface."""
import argparse,hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration
import numpy as np
import torch
from isaacgymenvs.deploy.wuji.temporal_policy_runtime import WujiTemporalPolicyRuntime
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--recorded-incoming-rnn',action='store_true',help='Diagnostic only: isolate one-step CPU/CUDA numerics with recorded incoming RNN.');a=p.parse_args();torch.set_num_threads(2)
 root=Path(__file__).resolve().parents[1];f=torch.load(a.fixture,map_location='cpu');s=torch.tensor(f['initial_states'],dtype=torch.float32);n=len(s);params=f['parameters']
 cfg=configuration('wuji_multigrasp',n,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','rl_device=cpu','sim_device=cpu'],train='wujiAcquisitionSAPG',seed=2026100211)
 runtime=WujiTemporalPolicyRuntime(cfg,root/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',root/'runs/unified-student-20261001/SA-real-51200/step_051200.pth',n=n)
 runtime.reset(s[:,:20],s[:,40:47],s[:,47:54],torch.tensor(params['handle_size']).repeat(n,1),torch.tensor(params['slider_size']).repeat(n,1),s[:,20:40])
 errors={k:0. for k in ['public','history','action','target','rnn']}
 step_errors=[]
 for step,row in enumerate(f['probes']):
  if a.recorded_incoming_rnn and step:runtime.player.states=[x.clone() for x in f['probes'][step-1]['rnn']]
  out=runtime.step(row['q'],row['obs'][:,95:96],applied_previous_action=row['previous_action'],issued_previous_targets=row['issued'])
  current={}
  for key,value in [('public',(out['public_observation']-row['obs'][:,:111]).abs().max()),('history',(out['student_observation']-row['x']).abs().max()),('action',(out['action']-row['action']).abs().max()),('rnn',max((x-y).abs().max() for x,y in zip(out['rnn_states'],row['rnn'])))]:current[key]=float(value);errors[key]=max(errors[key],float(value))
  step_errors.append(dict(step=step,**current))
  ids=torch.arange(20)[None]>=16
  expected=torch.where(ids,row['issued']+.025*row['action'],s[:,20:40]+.04*row['action']);expected=torch.maximum(torch.minimum(expected,runtime.upper),runtime.lower)
  errors['target']=max(errors['target'],float((out['joint_targets']-expected).abs().max()))
 thresholds=dict(public=2e-5,history=2e-5,action=2e-3,target=1e-4,rnn=2e-3);passed=all(errors[k]<thresholds[k] for k in errors)
 result=dict(passed=passed,recorded_incoming_rnn_diagnostic=a.recorded_incoming_rnn,step_errors=step_errors,fixture=str(a.fixture),fixture_sha256=hashlib.sha256(a.fixture.read_bytes()).hexdigest(),steps=len(f['probes']),batch=n,ids=f['ids'],geometry=params['label'],max_absolute_errors=errors,thresholds=thresholds,scope='CPU replay of recorded legal inputs/actions/RNN from physical H200 evaluation; no new physics or hardware, no current object/slider/contact truth consumed. Recorded incoming RNN mode is a one-step diagnostic, not autonomous state-maintenance parity.')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert passed,errors
if __name__=='__main__':main()
