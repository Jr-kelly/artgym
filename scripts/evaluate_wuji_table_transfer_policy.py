"""One deterministic development rollout; no fulltask/generalization claim."""
from pathlib import Path
import argparse,json,hashlib,numpy as np
from scripts.wuji_table_transfer_learning_env import TableTransferLearning
from scripts.train_wuji_table_transfer import PickupActor
import torch
p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);e=TableTransferLearning(n=1,seed=20261065,data='runs/flat-table-20261006/learning/table-transfer-20261006');m=PickupActor().cuda();m.load_state_dict(torch.load(a.checkpoint,map_location='cuda:0')['model']);rows=[]
try:
 obs=e.observation()
 while int(e.age[0])<e.steps:
  with torch.no_grad():d,v=m(obs);act=d.mean
  for j in range(min(5,e.steps-int(e.age[0]))):
   obs,r,done,info=e.step(act);rows.append(dict(time_s=float(e.age[0])/30,object=e.rb[0,e.object_index].cpu().numpy().copy(),q=e.dof[0,:,0].cpu().numpy().copy(),target=e.command_target[0].cpu().numpy().copy(),distance_m=float(info['relative_error'][0]),contact=e.contact[0].cpu().numpy().copy()))
 np.savez_compressed(a.output/'trace.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]});result=dict(checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),best_distance_m=min(r['distance_m'] for r in rows),final_distance_m=rows[-1]['distance_m'],final_object=rows[-1]['object'][:7].tolist(),failed=bool(e.failed[0]),support_frames=float(e.support_frames[0]),scope=__doc__);(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
finally:e.close()
