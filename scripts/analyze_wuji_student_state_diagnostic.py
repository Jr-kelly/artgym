"""Compare fixed student-state diagnostics to their original scored trajectories."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--original',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 probes=torch.load(a.directory/'latent-probes.pth',map_location='cpu')
 with np.load(a.directory/'trace.npz') as z:trace={k:z[k] for k in z.files}
 with np.load(a.original/'trace.npz') as z:original={k:z[k] for k in z.files}
 parity={k:bool(np.array_equal(trace[k],original[k])) for k in ['action','target','q','slider','object_pos','object_rot','goal','active'] if k in trace}
 assert all(parity.values()), 'Diagnostic changed scored trajectory; investigate before attributing snapshots to original'
 bad=(trace['drift']>=.01)|(trace['rotation']>=.25)|trace['fall'].astype(bool)|trace['invalid'].astype(bool)|~trace['active'].astype(bool)
 bad=np.maximum.accumulate(bad,axis=0);rows=[]
 for q in probes:
  n=len(q['label'])//4;k=q['step'];active=q['active'].bool().numpy()
  errors=torch.stack([(q['prediction']-q['label']).square().mean(1),(q['student_mean']-q['teacher_mean']).square().mean(1),(q['student_mean'].clamp(-1,1)-q['teacher_mean'].clamp(-1,1)).square().mean(1),(q['student_target']-q['teacher_target']).square().mean(1)],dim=1).numpy()
  prior=bad[k-1] if k else np.zeros(4*n,bool)
  for s in range(4):
   ids=np.arange(s*n,(s+1)*n);valid=active[ids];selected=ids[valid]
   values=errors[selected].mean(0).tolist() if len(selected) else [None]*4
   row=dict(pre_action_step=k,source=s,active_episodes=len(selected),prior_body_breach=int(prior[selected].sum()),latent_mse=values[0],raw_mean_mse=values[1],clipped_action_mse=values[2],target_mse_rad2=values[3])
   for label,mask in [('before_breach',~prior[selected]),('after_breach',prior[selected])]:
    row[label+'_episodes']=int(mask.sum());row[label+'_target_mse_rad2']=float(errors[selected[mask],3].mean()) if mask.any() else None
   rows.append(row)
 result=dict(trajectory_exact_parity=parity,diagnostic_trace_sha256=hashlib.sha256((a.directory/'trace.npz').read_bytes()).hexdigest(),original_trace_sha256=hashlib.sha256((a.original/'trace.npz').read_bytes()).hexdigest(),rows=rows,scope='Same episodes repeated only for independent diagnostics. Teacher labels never enter student action or optimization; times are not independent trials.')
 a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(exact_parity=all(parity.values()),rows=len(rows))))
if __name__=='__main__':main()
