"""Registered geometry assets, inheriting the exact bridge observation/control."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere
from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
class WujiGeometry(WujiBridge3Hemisphere):
 def _create_envs(self,*args,**kwargs):
  super()._create_envs(*args,**kwargs)
  # IsaacGym override_inertia=True derives inertia from shape density before
  # configured masses are assigned. Freeze the measured baseline, not merely
  # the authored URDF numbers. No inertia recomputation at the actor write.
  self.geometry_loaded_inertia=[]
  spec=json.loads((Path(__file__).resolve().parents[2]/'research/geometry-generalization-20261002/BASELINE_PHYSICS.json').read_text())
  for env,handle in zip(self.envs,self.object_handles):
   bodies=self.gym.get_actor_rigid_body_properties(env,handle)
   self.geometry_loaded_inertia.append([dict(ixx=b.inertia.x.x,iyy=b.inertia.y.y,izz=b.inertia.z.z) for b in bodies])
   for b,values in zip(bodies,spec['actual_inertia']):
    b.inertia.x.x=values['ixx'];b.inertia.y.y=values['iyy'];b.inertia.z.z=values['izz']
   self.gym.set_actor_rigid_body_properties(env,handle,bodies,False)
 def __init__(self,cfg,*args,**kwargs):
  root=Path(__file__).resolve().parents[2]
  source=root/'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
  assert hashlib.sha256(source.read_bytes()).hexdigest()=='056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
  self.hemisphere_reference=np.load(source)[0,43:47].copy()
  folder=root/cfg['object']['asset']['asset_root'];meta=json.loads((folder/'000/parameters.json').read_text())
  assert meta['round']==cfg['env'].get('geometryRound','geometry-generalization-20261002')
  assert hashlib.sha256((folder/'000/mobility.urdf').read_bytes()).hexdigest()==meta['urdf_sha256']
  WujiVariableTimedAcquisition.__init__(self,cfg,*args,**kwargs)
  states=np.load(root/cfg['env']['trainingStates']);assert states.shape[1]==75
  self.all_valid_states=torch.as_tensor(states,device=self.device);self.instance2grasplen[:]=len(states);self.instance_offsets[:]=0
