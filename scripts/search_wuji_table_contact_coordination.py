"""Task-directed finite contact coordination, actual36s development episodes; no full-flow proof."""
from scripts.wuji_table_transfer_learning_env import TableTransferLearning
import argparse,json,numpy as np,torch
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);e=TableTransferLearning(n=24,seed=20261066,data='runs/flat-table-20261006/learning/table-transfer-20261006');e.span[:7]=0.;e.span[15:]=0.;rng=np.random.default_rng(20261066);mu=np.zeros(12);std=np.full(12,.18);ids=np.r_[np.arange(7,15),np.arange(23,27)];log=(a.output/'search.jsonl').open('w',buffering=1);best=1e9
try:
 for batch in range(3):
  params=mu+rng.standard_normal((e.n,12))*std;params[0]=mu;params=np.clip(params,-.5,.5);trace=[];distances=[]
  while int(e.age[0])<e.steps:
   u=np.clip((int(e.age[0])/30-1)/3,0,1);u=u*u*(3-2*u);motor=e.path[e.age.clamp(max=e.steps-1)].clone();motor[:,ids]+=e.tensor(params)*float(u);e.servo(motor);obj=e.rb[:,e.object_index];distance=(obj[:,:3]-e.tensor([.31,-.625,.754])).norm(dim=-1);valid=(obj[:,2]>.750)&(obj[:,2]<.78)&(obj[:,0]>.300)&(obj[:,1]>-.630);cost=torch.where(valid,distance,torch.ones_like(distance));distances.append(cost.cpu().numpy());trace.append(dict(object=obj.cpu().numpy().copy(),target=e.command_target.cpu().numpy().copy(),q=e.dof[:,:,0].cpu().numpy().copy()));e.age+=1
  cost=np.array(distances);score=np.mean(cost[-60:],axis=0);rank=np.argsort(score);winner=int(rank[0]);row=dict(batch=batch,best_final_supported_distance_m=float(score[winner]),winner=winner,parameters=params[winner].tolist(),scope='Development score; native independent check required');log.write(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
  if score[winner]<best:
   best=float(score[winner]);np.savez_compressed(a.output/'best-rollout.npz',**{k:np.array([r[k][winner] for r in trace]) for k in trace[0]});(a.output/'best.json').write_text(json.dumps(row,indent=2))
  mu=params[rank[:5]].mean(0);std=np.maximum(params[rank[:5]].std(0),.025)
  if best<.03:break
  if batch<2:e.reset(torch.arange(e.n,device=e.device))
finally:e.close();log.close()
