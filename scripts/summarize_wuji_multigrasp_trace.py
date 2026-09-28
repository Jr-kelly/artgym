"""Independent per-grasp temporal/contact analysis of frozen physical traces."""
import argparse,json
from pathlib import Path
import numpy as np
FINGERS=['thumb','index','middle','ring','pinky']
def summarize(trace,stage_steps=60):
 active=trace['active'].astype(bool);valid=active&~trace['fall'].astype(bool)&~trace['invalid'].astype(bool);records=[]
 for i in range(active.shape[1]):
  mask=active[:,i];alive=bool(valid[:,i].all() and len(mask)==600);error=np.abs(trace['slider'][:,i]-trace['goal'][:,i]);body=(trace['drift'][:,i]<.01)&(trace['rotation'][:,i]<.25)
  stages=[];stages10=[]
  for start in range(0,600,stage_steps):
   end=start+stage_steps;slice_=slice(end-9,end)
   stages.append(bool(len(error[slice_])==9 and (error[slice_]<.002).all() and valid[slice_,i].all()))
   stages10.append(bool(len(error[slice_])==9 and (error[slice_]<.01).all() and valid[slice_,i].all()))
  consecutive=0
  for j in range(0,len(stages),2):
   if all(stages[j:j+2]):consecutive+=1
   else:break
  lost=[];contact=trace.get('contact')
  if contact is not None:
   for f,name in enumerate(FINGERS):
    present=contact[:,i,f]>0
    for t in range(1,len(present)-8):
     if present[:t].any() and not present[t:t+9].any() and mask[t]:lost.append(dict(finger=name,step=t,seconds=t/30));break
  failed=np.flatnonzero(~valid[:,i]);posefail=np.flatnonzero(~body&mask)
  records.append(dict(row=i,alive_full=alive,strict=alive and bool(body.all()) and all(stages),loose_all_endpoints=alive and all(stages10),complete_strict_cycles=sum(all(stages[j:j+2]) for j in range(0,len(stages),2)),consecutive_strict_cycles=consecutive,slider_mean_abs_error_mm=float(error[mask].mean()*1000),slider_max_abs_error_mm=float(error[mask].max()*1000),max_drift_mm=float(trace['drift'][mask,i].max()*1000),max_rotation_deg=float(np.rad2deg(trace['rotation'][mask,i].max())),first_terminal_seconds=float(failed[0]/30) if len(failed) else None,first_body_threshold_seconds=float(posefail[0]/30) if len(posefail) else None,first_sustained_contact_losses=sorted(lost,key=lambda x:x['step']),contact_fraction={name:float((contact[mask,i,j]>0).mean()) for j,name in enumerate(FINGERS)} if contact is not None else None,max_target_actual_error_rad=float(np.abs(trace['target'][mask,i]-trace['q'][mask,i]).max()),note='binary net force per distal finger is contact proxy, not per-object load/force decomposition; no causal claim'))
 return records
def main():
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--stage-seconds',type=int,choices=[2,5],default=2);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=summarize(np.load(a.trace),a.stage_seconds*30);a.output.write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
