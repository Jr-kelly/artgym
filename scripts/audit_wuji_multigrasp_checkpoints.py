"""Read saved checkpoints on CPU and audit epoch/frame identity without evaluation."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import torch
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--epoch',type=int,required=True);a=p.parse_args();rows=[]
 for arm in 'ABCD':
  path=R/'runs'/('mg_'+arm+'_seed2801')/'checkpoints'/('epoch_%06d.pth'%a.epoch)
  if not path.exists():rows.append(dict(arm=arm,status='missing'));continue
  cp=torch.load(path,map_location='cpu');rank=cp[0] if 0 in cp else cp
  finite=all(not v.is_floating_point() or torch.isfinite(v).all().item() for v in rank['model'].values())
  assert finite
  assert rank['epoch']==a.epoch
  frame=rank.get('frame');assert frame==163840*a.epoch,frame
  rows.append(dict(arm=arm,status='passed',epoch=rank['epoch'],frame=frame,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,model_tensor_count=len(rank['model']),optimizer_saved='optimizer' in rank,keys=sorted(rank.keys()),finite=finite))
 print(json.dumps(dict(scope='CPU checkpoint integrity only; no simulation, training update, model selection or success claim',rows=rows),indent=2))
if __name__=='__main__':main()
