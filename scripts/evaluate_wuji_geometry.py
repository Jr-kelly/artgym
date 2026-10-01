"""Physical geometry evaluator with actual asset/input/frozen-weight receipts."""
import argparse,hashlib,json,sys
from pathlib import Path
from scripts import evaluate_wuji_recovery as evaluator
import numpy as np
import torch
from scripts.wuji_student_interface import tensor_hash
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--states',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--model',choices=['teacher','student'],required=True);p.add_argument('--protocol',choices=['S2','S5','F'],required=True);p.add_argument('--video',action='store_true');p.add_argument('--fixture',action='store_true');a=p.parse_args()
 root=Path(__file__).resolve().parents[1];entry=json.loads((root/'research/geometry-generalization-20261002/ASSETS.json').read_text())[a.label]
 teacher='runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth';student='runs/unified-student-20261001/SA-real-51200/step_051200.pth'
 factory=evaluator.make_player;capture={};receipt={}
 def make_player(cfg,checkpoint):
  env,player=factory(cfg,checkpoint);player.model.eval()
  for v in player.model.parameters():v.requires_grad_(False)
  assert env.object_cfg['asset']['asset_root']=='assets/objects/'+entry['object']
  assert np.allclose(env.instance_link0_bbx.cpu(),entry['parameters']['handle_size'],atol=1e-7,rtol=0)
  assert np.allclose(env.instance_link1_bbx.cpu(),entry['parameters']['slider_size'],atol=1e-7,rtol=0)
  actor=env.gym.find_actor_handle(env.envs[0],'object');props=env.gym.get_actor_dof_properties(env.envs[0],actor);bodies=env.gym.get_actor_rigid_body_properties(env.envs[0],actor)
  spec=json.loads((root/'research/geometry-generalization-20261002/BASELINE_PHYSICS.json').read_text())
  for b,v in zip(bodies,spec['actual_inertia']):assert np.allclose([b.inertia.x.x,b.inertia.y.y,b.inertia.z.z],[v['ixx'],v['iyy'],v['izz']],rtol=1e-6,atol=1e-12)
  receipt.update(actual_mass=[x.mass for x in bodies],actual_inertia=[dict(ixx=x.inertia.x.x,iyy=x.inertia.y.y,izz=x.inertia.z.z) for x in bodies],actual_dof={k:props[k].tolist() for k in props.dtype.names},asset=entry,student_legal_inputs=a.model=='student')
  original=env._compute_sapg_priv_observations;calls=[0]
  def observations():
   policy,priv=original();expected=torch.tensor(np.array(entry['parameters']['handle_size'])[[0,2,1]],device=env.device,dtype=torch.float32)
   assert torch.allclose(policy[:,49:52],expected.expand(env.num_envs,-1),atol=1e-7,rtol=0)
   if calls[0]==0:receipt.update(first_public_initial55=policy[:,:55].cpu().tolist(),raw_bbox=policy[0,49:55].cpu().tolist())
   calls[0]+=1;return policy,priv
  env._compute_sapg_priv_observations=observations
  # Unified encoder is installed by evaluator after this factory returns.
  original_configure=env.configure_fixed_grasp_consecutive_evaluation
  def configure(*args,**kwargs):
   capture['before']=tensor_hash(player.model.state_dict());return original_configure(*args,**kwargs)
  env.configure_fixed_grasp_consecutive_evaluation=configure
  capture.update(player=player,calls=calls)
  if a.fixture:
   assert a.model=='student'
   action_fn=player.get_action;probes=[];ids=torch.linspace(0,env.num_envs-1,8,device=env.device).long()
   def action(obs,*args,**kwargs):
    row=dict(q=env.hand_dof_pos[ids].cpu().clone(),obs=obs[ids].cpu().clone(),x=env.student_obs_buf[ids].cpu().clone(),previous_action=env.actions[ids].cpu().clone(),issued=env.known_controller.issued[ids].cpu().clone()) if len(probes)<64 else None
    result=action_fn(obs,*args,**kwargs)
    if row is not None:
     row.update(action=result[ids].cpu().clone(),rnn=[s[:,ids].cpu().clone() for s in player.states]);probes.append(row)
    return result
   player.get_action=action;capture.update(probes=probes,fixture_ids=ids.cpu().tolist())
  return env,player
 evaluator.make_player=make_player
 argv=sys.argv
 try:
  sys.argv=[argv[0],'--checkpoint',teacher,'--task','wuji_geometry','--hand','wuji_paper_official_actuator','--object',entry['object'],'--initial-states',a.states,'--output',str(a.output),'--seed','2026100209','--stage-seconds','5' if a.protocol=='S5' else '2','--protocol','F' if a.protocol=='F' else 'S']
  if a.model=='student':sys.argv+=['--unified-student',student]
  if a.video:sys.argv+=['--video','--video-columns','3']
  evaluator.main()
  assert capture['before']==tensor_hash(capture['player'].model.state_dict())
  receipt.update(model_unchanged=True,observation_checks=capture['calls'][0],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol=a.protocol,model=a.model)
  (a.output/'geometry-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
  if a.fixture:torch.save(dict(probes=capture['probes'],ids=capture['fixture_ids'],initial_states=np.load(a.states)[capture['fixture_ids']],parameters=entry['parameters']),a.output/'legal-replay-fixture.pth')
 finally:evaluator.make_player=factory;sys.argv=argv
if __name__=='__main__':main()
