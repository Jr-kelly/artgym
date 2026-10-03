"""Actual frozen750 offline latency on authorized computer, no SDK or physics."""
import pathlib,sys,runpy,time,json,argparse
import isaacgym
import torch
import numpy as np
from scripts.g2_r800_policy import G2R800Policy
p=argparse.ArgumentParser();p.add_argument('--timing-output',type=pathlib.Path,required=True);a,rest=p.parse_known_args();samples=[];original=G2R800Policy.command;original_prewarm=G2R800Policy.prewarm;warming=False
def measured(self,*args,**kwargs):
 torch.cuda.synchronize();start=time.perf_counter();result=original(self,*args,**kwargs);torch.cuda.synchronize();
 if not warming:samples.append((time.perf_counter()-start)*1000)
 return result
def isolated_prewarm(self,*args,**kwargs):
 global warming
 warming=True
 try:return original_prewarm(self,*args,**kwargs)
 finally:warming=False
G2R800Policy.prewarm=isolated_prewarm
G2R800Policy.command=measured;sys.argv=['scripts.replay_wuji_support_commands']+rest
runpy.run_module('scripts.replay_wuji_support_commands',run_name='__main__');values=np.array(samples);r=dict(frames=len(values),first_ms=float(values[0]),median_ms=float(np.median(values[1:])),p95_ms=float(np.percentile(values[1:],95)),maximum_ms=float(values.max()),samples_over_30hz_period=int((values>1000/30).sum()),mean_ms=float(values.mean()),gpu=torch.cuda.get_device_name(),scope='Single measured/issued continuous-record replay; synchronizedCUDA inference timing only, includesfrozenencoder/residual/modelFK. ExcludesSDK transport, serial/motorPD, hostmeasurement andscene simulation. Not realrobot latency guarantee or policybehavior test.')
a.timing_output.parent.mkdir(parents=True,exist_ok=True);a.timing_output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
