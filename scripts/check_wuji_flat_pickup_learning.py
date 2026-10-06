import argparse,json
from pathlib import Path
from scripts.wuji_flat_pickup_learning_env import FlatPickupLearning
import torch,numpy as np
p=argparse.ArgumentParser();p.add_argument('--envs',type=int,default=8);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);e=FlatPickupLearning(a.envs);source=np.load(e.data/'prefix.npz');obj=e.rb[:,e.object_index].cpu().numpy();expected=source['expected_object'];dist=np.linalg.norm(obj[:,:3]-expected[:3],axis=1);out=dict(n=a.envs,endpoint_object_m=obj[:,:7].tolist(),prior_object=expected[:7].tolist(),endpoint_error_m=dist.tolist(),initial_clearance_m=e.clearance().cpu().tolist(),obs_shape=list(e.observation().shape),scope='real flat-start motor replay; endpoint parity diagnostic, not pickup success');print(json.dumps(out),flush=True)
for i in range(e.steps):o,r,d,info=e.step(torch.zeros(e.n,27,device=e.device))
out.update(zero_policy_final_clearance_m=info['clearance'].cpu().tolist(),zero_policy_held_frames=info['held_frames'].cpu().tolist());(a.output/'result.json').write_text(json.dumps(out,indent=2));e.close()
