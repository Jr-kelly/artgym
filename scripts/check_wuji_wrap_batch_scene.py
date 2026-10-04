"""One matched n=1/n=8 physical comparison before adapting or expanding training.

Native single-run evaluation remains authoritative for frozen functional
criteria and pair contact forces. Batch contact proxies are reported as proxies.
"""
from isaacgym import gymapi
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
import torch
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic

def main():
 p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--envs',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);saved=torch.load(a.checkpoint,map_location='cuda');spec=json.loads(a.scene.read_text());reference=json.loads(a.reference.read_text());model=ResidualActorCritic(154,181).to('cuda');model.load_state_dict(saved['model']);model.eval();scale=torch.tensor(saved['action_scale'],device='cuda')
 scene=G2ContinuousScene(n=a.envs,seed=2026100407,randomization_scale=0.,instances=['000']*a.envs,load_min=.2,load_max=.2,detent_min=.2,detent_max=.2,reference_spec=reference,support_scale=.025,thumb_scale=.12,scene_spec=spec,takeover_seconds=16.,load_profile='constant',action_parameterization='bounded-motor-offset',resistance_integration='solver-brake',compact_isolated_layout=True)
 frames=[];start=time.monotonic()
 try:
  np.savez_compressed(a.output/'initial.npz',root=scene.root.cpu().numpy(),dof=scene.dof.cpu().numpy(),cal_object=scene.cal_object.cpu().numpy(),cal_slider=scene.cal_slider.cpu().numpy(),materials=scene.material_tensor.cpu().numpy())
  for step in range(1080):
   public,critic=scene.features()
   with torch.no_grad():residual=model.actor_logits(public)
   scene.step(residual,scale,reset_failed=False,reset_finished=False)
   f={k:v.cpu().numpy().copy() for k,v in scene.last_diagnostics.items()};f['motor_target']=scene.command_target[:,scene.hand_ids].cpu().numpy().copy();f['arm_q']=scene.dof[:,scene.arm_ids,0].cpu().numpy().copy();f['hand_q']=scene.dof[:,scene.hand_ids,0].cpu().numpy().copy();f['object_state']=scene.rb[:,scene.object_index].cpu().numpy().copy();f['wrist_state']=scene.rb[:,scene.wrist_index].cpu().numpy().copy();frames.append(f)
   if step%150==0:print(json.dumps(dict(step=step,height=f['height'].tolist(),slider=f['slider'].tolist())),flush=True)
  np.savez_compressed(a.output/'trace.npz',**{k:np.stack([f[k] for f in frames]) for k in frames[0]});result=dict(scope=__doc__,n=a.envs,scene=str(a.scene),checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),wall_seconds=time.monotonic()-start,episodes=scene.stats,held_diagnostic=True,continuous_pickup_demo_pass=False,full_functional_pair_force_validation=False);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 finally:scene.close()

if __name__=='__main__':main()
