"""Small physical compatibility check; scene declares held versus actual pickup."""
import argparse,json,time
from pathlib import Path
from isaacgym import gymapi
import torch,numpy as np
from scripts.g2_continuous_scene import G2ContinuousScene

def main():
 p=argparse.ArgumentParser();p.add_argument('--episodes',type=int,default=1);p.add_argument('--trace-envs',type=int);p.add_argument('--randomization-scale',type=float,default=0.);p.add_argument('--stochastic-residual',action='store_true');p.add_argument('--disabled-perturbations',default='');p.add_argument('--geometry-schedule',type=Path);p.add_argument('--checkpoint',type=Path);p.add_argument('--asset-registry',type=Path);p.add_argument('--scene',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=8);p.add_argument('--known-support-span',type=float,default=.04);p.add_argument('--takeover-seconds',type=float,default=16.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
 saved=torch.load(a.checkpoint,map_location='cpu') if a.checkpoint else None
 registry=json.loads(a.asset_registry.read_text()) if a.asset_registry else None
 asset_registry={r['instance']:r['directory'] for r in registry['entries']} if registry else None
 instances=json.loads(a.geometry_schedule.read_text())['instances'] if a.geometry_schedule else [next(iter(asset_registry))] if registry else ['000']
 if a.geometry_schedule:assert len(instances)==a.envs and asset_registry and all(sid in asset_registry for sid in instances)
 scale=saved['action_scale'] if saved else [.04]*16+[.15]*4
 s=G2ContinuousScene(a.envs,2026100421,a.randomization_scale,disabled_perturbations=tuple(filter(None,a.disabled_perturbations.split(','))),instances=instances,asset_registry=asset_registry,scene_spec=json.loads(a.scene.read_text()),reference_spec=json.loads(a.reference.read_text()),resistance_integration='solver-brake',load_min=.2,load_max=.2,detent_min=.2,detent_max=.2,load_profile='constant',action_parameterization='bounded-motor-offset',support_scale=float(scale[0]),thumb_scale=float(scale[16]),known_support_span=a.known_support_span,takeover_seconds=a.takeover_seconds)
 actor=None
 if saved:
  import hashlib
  from scripts.wuji_robust_learning import ResidualActorCritic,TEACHER,R800
  assert saved['format']=='wuji-r800-residual-ppo-v1' and saved['public_dim']==154 and not saved.get('support_delta_spec') and saved['action_parameterization']=='bounded-motor-offset'
  assert saved['teacher_sha256']==hashlib.sha256(TEACHER.read_bytes()).hexdigest() and saved['student_sha256']==hashlib.sha256(R800.read_bytes()).hexdigest()
  actor=ResidualActorCritic(154,181).to('cuda');actor.load_state_dict(saved['model']);actor.eval()

 assert a.episodes in [1,2]
 trace_ids=np.arange(a.envs) if a.trace_envs is None else np.linspace(0,a.envs-1,min(a.envs,a.trace_envs),dtype=int)
 frames=[];start=time.monotonic()
 try:
  for i in range(1080*a.episodes):
   if i and i%1080==0:s.reset(torch.arange(a.envs,device=s.device))
   with torch.no_grad():
    public,_=s.features();logits=actor.actor(public) if actor is not None else torch.zeros((a.envs,20),device='cuda')
   if a.stochastic_residual:
    assert actor is not None
    logits=logits+torch.randn_like(logits)*actor.logstd.clamp(-3.5,-.4).exp()
   s.step(logits,reset_failed=False,reset_finished=False)
   frames.append({k:v[trace_ids].cpu().numpy().copy() for k,v in s.last_diagnostics.items()})
   if i%240==0:print(json.dumps(dict(frame=i,height=float(s.last_diagnostics['height'].mean()))),flush=True)
  np.savez_compressed(a.output/'trace.npz',**{k:np.stack([f[k] for f in frames]) for k in frames[0]});r=dict(physical_episodes_requested=a.episodes,trace_env_indices=trace_ids.tolist(),randomization_scale=a.randomization_scale,disabled_perturbations=a.disabled_perturbations,stochastic_residual=a.stochastic_residual,scope=('Held-only parallel physical compatibility probe' if s.held_diagnostic else 'Actual table pickup and two-cycle parallel physical compatibility probe')+'; nominal development only, not independent generalization validation',known_controller_spec=s.known_controller_spec,episodes=s.stats,wall_seconds=time.monotonic()-start);(a.output/'report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
 finally:s.close()
if __name__=='__main__':main()
