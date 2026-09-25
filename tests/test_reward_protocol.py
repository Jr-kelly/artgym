import ast,json,types,subprocess
from pathlib import Path
import torch

# Execute the exact reward/goal methods without constructing a simulator.
source=Path('isaacgymenvs/tasks/artmanip.py').read_text()
names=['compute_reward','update_goal','_get_next_goal_offsets','_reset_training_goal_success_state','_activate_eval_session']
tree=ast.parse(source)
functions=[x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name in names]
ns={'torch':torch,'quat_conjugate':lambda q:torch.cat([-q[:,:3],q[:,3:]],dim=1),
    'quat_mul':lambda a,b:torch.tensor([[0.,0.,0.,1.]]).expand_as(a),
    'to_torch':lambda values,**kw:torch.tensor(values,**kw)}
# All orientations below are identity; the quaternion helpers are exact there.
exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-artmanip-methods>','exec'),ns)

def environment(protocol="corrected", fallen=False,old_best=.002):
 e=types.SimpleNamespace()
 for name in names:setattr(e,name,types.MethodType(ns[name],e))
 e.cfg={"env":{"rewardProtocol":protocol}}
 e.eval_mode=False;e.object_cfg={'task':{'success_threshold':.005,'contact_num':5}}
 e.obj_dof_pos=torch.tensor([[.039]]);e.goal_obj_dof_pos=torch.tensor([[.04]])
 e.goal_achieved_step=torch.zeros(1);e.goal_achieved_latch=torch.zeros(1,dtype=torch.bool)
 e.training_success_hold_time=torch.zeros(1);e.success_hold_steps_dt=1/120
 e.goal_timer=torch.zeros(1);e.training_goal_success_counted=torch.zeros(1,dtype=torch.bool)
 e.goal_refresh_interval=torch.zeros(1);e.successes=torch.zeros(1)
 e.max_consecutive_successes=2;e.goal_switch_timeout_sec=12.
 e.debug_reset_cause_success_budget=torch.zeros(1,dtype=torch.bool)
 e.reset_buf=torch.tensor([int(fallen)]);e.truncated_envs=torch.tensor([fallen])
 e.goal_indices=torch.zeros(1,dtype=torch.long);e.goal_offsets=torch.tensor([.04,0.])
 e.init_obj_dof_pos=torch.zeros(1,1);e.mini_goal_distance=torch.tensor([old_best])
 e.object_pos=torch.zeros(1,3);e.prev_object_pos=torch.zeros(1,3)
 e.object_rot=torch.tensor([[0.,0.,0.,1.]]);e.prev_object_rot=e.object_rot.clone()
 e.hand_dof_pos=torch.zeros(1,20);e.init_hand_dof_pos=torch.zeros(1,20)
 e.contact_info=torch.ones(1,5);e.episode_goal_distance_reward1_sum=torch.zeros(1)
 e.cur_targets=torch.zeros(1,21);e.actuated_dof_indices=torch.arange(20)
 e.prev_reward_targets=torch.zeros(1,20);e.rew_buf=torch.zeros(1);e.extras={}
 e.reward_scales_current=dict(GoalDistance1=1000.,GoalDistance2=1.,ObjPosDeviation=-50.,ObjRotDeviation=-2.,
                             StableContact=1.,HandQposDeviation=-.001,Smooth=-1.,Drop=-1.,Success=50.)
 e._get_reward_curriculum_metrics=lambda:{}
 return e

import unittest

class RewardAccountingTests(unittest.TestCase):
 def test_paper_eval_runs_without_undocumented_stage_timeout(self):
  for protocol in ('paper','upstream'):
   e=environment(protocol);e.device='cpu';e.goal_switch_timeout_sec=0.
   e._reset_eval_session_buffers=lambda:None
   kwargs=dict(instance_index=0,grasp_states=torch.zeros(1,79),grasp_split='valid',
               episodes_per_grasp=1,goal_sequence=[.04,0.],stage_duration=None)
   if protocol=='paper':
    e._activate_eval_session(**kwargs);self.assertEqual(e.eval_goal_timeout,0.)
   else:
    with self.assertRaises(ValueError):e._activate_eval_session(**kwargs)
 def step(self,e):
  e.compute_reward(torch.zeros(1,20))
  return float(e.extras['GoalDistance1'])
 def test_upstream_bug_is_preserved_for_control(self):
  e=environment('upstream')
  self.assertAlmostEqual(self.step(e),38,places=4)
 def test_switch_credits_only_old_goal_progress(self):
  e=environment()
  self.assertAlmostEqual(self.step(e),1,places=4)
  self.assertAlmostEqual(float(e.mini_goal_distance[0]),.039,places=6)
  self.assertEqual(float(e.successes[0]),1)
  e.obj_dof_pos[:]=.038
  self.assertAlmostEqual(self.step(e),1,places=4)
 def test_full_cycle_counts_two_stages(self):
  e=environment();self.step(e)
  e.obj_dof_pos[:]=.001
  self.step(e)
  self.assertEqual(float(e.successes[0]),2)
  self.assertEqual(int(e.reset_buf[0]),1)
 def test_dropped_success_does_not_count(self):
  e=environment(fallen=True)
  self.assertEqual(self.step(e),0)
  self.assertEqual(float(e.extras['Success']),0)
  self.assertEqual(float(e.successes[0]),0)
  self.assertAlmostEqual(float(e.goal_obj_dof_pos[0]),.04,places=6)
 def test_rewards_match_away_from_switch(self):
  a,b=environment('upstream'),environment('corrected')
  for e in (a,b):e.obj_dof_pos[:]=.025;e.mini_goal_distance[:]=.016
  self.step(a);self.step(b)
  torch.testing.assert_close(a.rew_buf,b.rew_buf)
 def test_paper_action_smoothing_and_physical_velocity(self):
  e=environment('paper')
  e.obj_dof_pos[:]=.025
  e.actions=torch.ones(1,20)*.1
  e.previous_policy_actions=torch.zeros(1,20)
  e.object_linvel=torch.tensor([[.1,0,0]])
  e.object_angvel=torch.tensor([[0,0,.2]])
  self.step(e)
  self.assertAlmostEqual(float(e.extras['Smooth']),-.2,places=5)
  self.assertAlmostEqual(float(e.extras['ObjPosDeviation']),-5,places=5)
  self.assertAlmostEqual(float(e.extras['ObjRotDeviation']),-.4,places=5)

 def test_evaluation_switch_uses_correct_stage_distance(self):
  e=environment();e.eval_mode=True;e.device='cpu'
  e.eval_active_mask=torch.ones(1,dtype=torch.bool)
  e.success_hold_duration=0.;e.eval_goal_timeout=0.
  e.eval_goal_stage=torch.zeros(1,dtype=torch.long)
  e.eval_consecutive_mode=True;e.eval_consecutive_success_cycles=torch.zeros(1)
  e._finalize_eval_stage=lambda *args,**kwargs:None
  e._reset_eval_episode_state=lambda *args:None
  def set_goal(ids,stage):
   e.eval_goal_stage[ids]=stage
   e.goal_obj_dof_pos[ids]=.04 if stage==0 else 0.
   e.mini_goal_distance[ids]=(e.obj_dof_pos[ids]-e.goal_obj_dof_pos[ids]).abs().flatten()
  e._set_eval_goal_targets=set_goal
  self.assertAlmostEqual(self.step(e),1,places=4)
  self.assertAlmostEqual(float(e.mini_goal_distance[0]),.039,places=6)
  e.obj_dof_pos[:]=.001
  self.step(e)
  self.assertEqual(float(e.eval_consecutive_success_cycles[0]),1)

 def test_invalid_numeric_state_never_earns_success(self):
  e=environment();e.obj_dof_pos[:]=float('nan')
  self.assertEqual(self.step(e),0)
  self.assertEqual(float(e.extras['Success']),0)
  self.assertTrue(torch.isfinite(e.rew_buf).all())

if __name__=='__main__': unittest.main(verbosity=2)
