"""Small physical compatibility check of explicitly held-only newgrasp module."""
import argparse,json,time
from pathlib import Path
from isaacgym import gymapi
import torch,numpy as np
from scripts.g2_continuous_scene import G2ContinuousScene

def main():
 p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=8);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
 s=G2ContinuousScene(a.envs,2026100421,0.,instances=['000'],scene_spec=json.loads(a.scene.read_text()),reference_spec=json.loads(a.reference.read_text()),resistance_integration='solver-brake',load_min=.2,load_max=.2,detent_min=.2,detent_max=.2,load_profile='constant',action_parameterization='bounded-motor-offset',support_scale=.04,thumb_scale=.15)
 frames=[];start=time.monotonic()
 try:
  for i in range(1080):
   s.step(torch.zeros((a.envs,20),device='cuda'),reset_failed=False,reset_finished=False)
   frames.append({k:v.cpu().numpy().copy() for k,v in s.last_diagnostics.items()})
   if i%240==0:print(json.dumps(dict(frame=i,height=float(s.last_diagnostics['height'].mean()))),flush=True)
  np.savez_compressed(a.output/'trace.npz',**{k:np.stack([f[k] for f in frames]) for k in frames[0]});r=dict(scope='Held-only parallelphysicalcompatibility probe, not continuouspickup/generalization validation',episodes=s.stats,wall_seconds=time.monotonic()-start);(a.output/'report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
 finally:s.close()
if __name__=='__main__':main()
