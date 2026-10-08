"""Exercise real caller methods without creating or stepping a simulator."""
import ast
import io
import json
import hashlib
import shutil
import tempfile
import types
from unittest.mock import patch
from pathlib import Path
import unittest
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.wuji_regrasp_contract import (
    phase_increment, entry_progress_reward, LEGACY_TIMING,
)


def method(filename, class_name, name):
    tree=ast.parse(Path(filename).read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name)
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    module=ast.Module(body=[node],type_ignores=[])
    namespace=dict(np=np,torch=torch,json=json,Rotation=Rotation,
                   phase_increment=phase_increment,entry_progress_reward=entry_progress_reward)
    exec(compile(module,filename,'exec'),namespace)
    return namespace[name]


class RegraspContract(unittest.TestCase):
    def test_capacity_caller_uses_selected_original_closed_baseline(self):
        # Isolate measurement/acceptance, supplying synthetic motor/geometry
        # collaborators; this test does not claim physical B capacity.
        source=Path('scripts/wuji_fresh_capacity_probe.py')
        tree=ast.parse(source.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='probe')
        class Box:pass
        class Skill:
            def __init__(self,cfg,spec,output):self.taken=True;self.push_slider_start=cfg['push_start']
            def command(self,t,O,arm,hand,issued_arm,issued_hand,slider):return issued_arm,issued_hand
        fake_geometry=types.ModuleType('scripts.check_wuji_action_quality')
        class H:
            def inspect(self,q):return []
        fake_geometry.HandIntersection=H
        namespace=dict(Path=Path,np=np,json=json,hashlib=hashlib,shutil=shutil,
                       __file__=str(source.resolve()),__doc__='Synthetic caller acceptance contract',
                       record=lambda *a,**k:None,RetainedPushSkill=Skill,transform=lambda *a:np.eye(4))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
        with tempfile.TemporaryDirectory() as tmp,patch.dict('sys.modules',{'scripts.check_wuji_action_quality':fake_geometry}):
            for index,(start,finish,passes) in enumerate([(0.,.025,True),(-.009,.017,False),(0.,.020,False)]):
                e=Box();e.cfg={'push_start':start};e.initial_slider=torch.tensor([.011,0.,-.004]);e.command_target=torch.zeros((3,27));e.dof=torch.zeros((3,28,2));e.rb=torch.zeros((3,1,13));e.object_index=0;e.steps=0
                e.dof[1,27,0]=start;e.tensor=torch.as_tensor;e.whole_clearance=lambda:torch.ones(3)*.1
                def servo(motor):
                    e.steps+=1;e.dof[1,27,0]=start+(finish-start)*min(e.steps/150.,1.)
                e.servo=servo
                with patch('sys.stdout',io.StringIO()):result=namespace['probe'](e,1,Path(tmp)/str(index))
                self.assertEqual(e.steps,300);self.assertEqual(result['original_closed_slider_q_m'],0.)
                self.assertEqual(result['capacity_pass'],passes)
                if passes:self.assertEqual(result['reward'],20.)
                else:self.assertLess(result['reward'],0.)
                if start<0:self.assertGreater(result['last1s_min_m'],.02);self.assertLess(result['absolute_extension_last1s_min_m'],.02)

    def test_vector_mapping_and_legacy_compatibility(self):
        a=np.array([-1.,-.75,-.5,0.,.5,1.])
        expected=np.array([0.,0.,0.,1.,2.,2.])
        np.testing.assert_array_equal(phase_increment(a),expected)
        np.testing.assert_array_equal(phase_increment(torch.tensor(a)).numpy(),expected)
        np.testing.assert_allclose(phase_increment(a,LEGACY_TIMING),1+.75*a)
        with self.assertRaises(ValueError):phase_increment(a,'unknown')

    def test_stationary_hold_cannot_accumulate_positive_reward(self):
        self.assertLess(entry_progress_reward(.5,.5,0.,0.,1.),0)
        score=sum(entry_progress_reward(.9,.9,1. if i<30 else 0.,float(i==29),1.) for i in range(240))
        self.assertAlmostEqual(score,0.)
        self.assertLess(entry_progress_reward(.9,0.,0.,0.,0.),-10)
        # Identical endpoint potential gives no net progress bonus.
        self.assertAlmostEqual(sum(entry_progress_reward(a,b,0.,0.,1.)+.05
                                  for a,b in [(0.,.8),(.8,.2),(.2,.8),(.8,0.)]),0.)

    def test_native_pause_keeps_motor_control_active(self):
        class Kin:
            def forward(self,q):return np.eye(4)
            def solve_near(self,T,q,max_step):return q.copy(),{'position_m':0.}
        class Policy:pass
        p=Policy();p.warmed=True;p.correction=np.eye(4);p.kin=Kin()
        p.goal=np.array([0.,0.,0.,0.,0.,0.,1.]);p.goal_q=np.zeros(20)
        p.motor=np.ones((3,27));p.motor[0]=0
        p.phase=0.;p.tick=1;p.episode_steps=240;p.action_period=5
        p.action=np.zeros(28);p.action[0]=.3;p.action[27]=-.75
        p.span=np.ones(27)*.2;p.slew=np.ones(27)*.006;p.offset=np.zeros(27)
        p.timing='pause-linear-v2';p.stream=io.StringIO()
        command=method('scripts/wuji_regrasp_reference_policy.py','RegraspReferencePolicy','command')
        arm,hand=command(p,np.eye(4),np.zeros(27),np.zeros(27),np.zeros(27),np.zeros((0,3)),[])
        self.assertEqual(p.phase,0.);self.assertEqual(p.tick,2)
        self.assertGreater(arm[0],0.);self.assertEqual(json.loads(p.stream.getvalue())['phase_increment'],0.)

    def test_training_pause_matches_native_and_preserves_offsets(self):
        class Env:pass
        e=Env();e.n=2;e.phase=torch.zeros(2);e.offset=torch.zeros((2,27));e.span=torch.ones(27)*.2
        e.slew=torch.ones(27)*.006;e.motor_reference=torch.zeros((3,27));e.pause_steps=torch.zeros(2)
        e.age=torch.zeros(2);e.steps=240;e.failed=torch.zeros(2,dtype=torch.bool)
        e.entry_frames=torch.zeros(2);e.best_entry_dwell=torch.zeros(2);e.entry_awarded=torch.zeros(2,dtype=torch.bool)
        e.held_frames=torch.zeros(2);e.max_held_frames=torch.zeros(2);e.best_entry_error=torch.ones(2)*float('inf')
        e.previous_potential=torch.ones(2)*.5;e.last=torch.zeros((2,27))
        e.guide_targets=lambda:torch.zeros((2,27));e.servo=lambda q:setattr(e,'issued',q.clone())
        e.observation=lambda:torch.zeros((2,149))
        e.entry_metrics=lambda:dict(held=torch.ones(2,dtype=torch.bool),finite=torch.ones(2,dtype=torch.bool),
            clearance_m=torch.ones(2)*.03,position_m=torch.ones(2)*.02,rotation_rad=torch.ones(2),
            q_rms_rad=torch.ones(2),error=torch.ones(2),potential=torch.ones(2)*.5)
        action=torch.zeros((2,28));action[:,0]=.3;action[:,27]=-.75
        step=method('scripts/wuji_regrasp_learning.py','RegraspLearning','step')
        _,reward,_,info=step(e,action)
        self.assertTrue((e.phase==0).all());self.assertTrue((e.issued[:,0]>0).all())
        self.assertTrue((reward<0).all());self.assertTrue((info['phase_increment']==0).all())


    def test_fresh_native_increment_retains_joint_anchor_and_total_slew(self):
        class Box:pass
        class Kin:
            def forward(self,q):return np.eye(4)
        class Hand:
            def forward(self,q):return {'hand_r_thumb_pad_link':np.eye(4)}
        p=Box();p.incremental=True;p.warmed=True;p.slider_start=None;p.entry_dwell=0;p.entry_ready=False;p.spec={};p.kin=Kin();p.geometry=Box();p.geometry.w=Hand();p.geometry.knife_geometry=Box()
        g=p.geometry.knife_geometry;g.joint_xyz=np.zeros(3);g.joint_r=np.eye(3);g.axis=np.array([0,0,1.])
        p.pad_vertices=np.zeros((1,3));p.slider_half=np.ones(3)*.01;p.low=np.ones(27)*-2;p.high=np.ones(27)*2
        p.motor=np.zeros((3,27));p.motor[1:]=1.;p.correction=np.ones(27)*.1
        p.goal=np.array([0.,0.,0.,0.,0.,0.,1.]);p.goal_q=np.zeros(20);p.phase=0.;p.tick=1;p.episode_steps=900;p.action_period=2
        p.action=np.zeros(28);p.action[0]=.3;p.action[27]=-.75;p.span=np.ones(27)*.2;p.slew=np.ones(27)*.006;p.offset=np.zeros(27);p.timing='pause-linear-v2';p.stream=io.StringIO()
        command=method('scripts/wuji_regrasp_reference_policy.py','RegraspReferencePolicy','command')
        issued=np.ones(27)*.1
        arm,hand=command(p,np.eye(4),np.zeros(27),np.zeros(27),issued,np.zeros((0,3)),[],object_velocity=np.zeros(6),slider=0.,slider_velocity=0.)
        target=np.r_[arm,hand];self.assertEqual(p.phase,0.);self.assertAlmostEqual(target[0],.1018);np.testing.assert_allclose(target[1:],issued[1:])
        # A violent guide change is still bounded by total issued-motor slew,
        # while the same new checkpoint retains incremental rather than v2 target-offset semantics.
        p.tick=3;p.action[27]=0.
        arm,hand=command(p,np.eye(4),np.zeros(27),np.zeros(27),target,np.zeros((0,3)),[],object_velocity=np.zeros(6),slider=0.,slider_velocity=0.)
        np.testing.assert_allclose(np.r_[arm,hand]-target,p.slew);self.assertEqual(p.phase,1.)


    def test_long_workspace_credit_does_not_reward_early_drop_or_static_pause(self):
        gamma=.999;cost=-.05;loss=-60.
        holding=sum(cost*gamma**t for t in range(900))
        for frames in [30,120,450]:
            premature=sum(cost*gamma**t for t in range(frames))+loss*gamma**frames
            self.assertLess(premature,holding)
        for error in [0.,2.,4.,8.]:
            potential=np.clip(1-error/8,0,1)
            self.assertLess(entry_progress_reward(potential,potential,0.,0.,1.),0.)

    def test_free27_native_and_training_move_joints_without_future_reference(self):
        class Box:pass
        class Kin:
            def forward(self,q):return np.eye(4)
        class Hand:
            def forward(self,q):return {'hand_r_thumb_pad_link':np.eye(4)}
        p=Box();p.free_motor=True;p.incremental=True;p.warmed=True;p.slider_start=None;p.entry_dwell=0;p.entry_ready=False;p.spec={};p.kin=Kin();p.geometry=Box();p.geometry.w=Hand();p.geometry.knife_geometry=Box()
        g=p.geometry.knife_geometry;g.joint_xyz=np.zeros(3);g.joint_r=np.eye(3);g.axis=np.array([0,0,1.])
        p.pad_vertices=np.zeros((1,3));p.slider_half=np.ones(3)*.01;p.low=np.ones(27)*-2;p.high=np.ones(27)*2
        p.motor=np.zeros((3,27));p.motor[1:]=10.;p.correction=np.ones(27)*.1
        p.goal=np.array([0.,0.,0.,0.,0.,0.,1.]);p.goal_q=np.zeros(20);p.phase=0.;p.tick=1;p.episode_steps=900;p.action_period=2
        p.action=np.zeros(27);p.action[0]=.3;p.action[26]=.4;p.span=np.ones(27)*.6;p.slew=np.ones(27)*.006;p.offset=np.zeros(27);p.timing='free-motor-hold-v7';p.stream=io.StringIO()
        command=method('scripts/wuji_regrasp_reference_policy.py','RegraspReferencePolicy','command');issued=np.ones(27)*.1
        arm,hand=command(p,np.eye(4),np.zeros(27),np.zeros(27),issued,np.zeros((0,3)),[],object_velocity=np.zeros(6),slider=0.,slider_velocity=0.)
        native=np.r_[arm,hand];self.assertEqual(p.phase,0.);self.assertAlmostEqual(native[0],.1018);self.assertAlmostEqual(native[26],.1024)
        e=Box();e.n=1;e.device='cpu';e.free_motor=True;e.task_geometry=False;e.functional_workspace=False;e.phase=torch.zeros(1);e.offset=torch.zeros((1,27));e.span=torch.ones(27)*.6;e.slew=torch.ones(27)*.006;e.motor_reference=torch.tensor(p.motor,dtype=torch.float32);e.motor_anchor=torch.ones((1,27))*.1;e.command_target=torch.ones((1,27))*.1;e.limitlow=torch.ones(27)*-2;e.limithi=torch.ones(27)*2;e.pause_steps=torch.zeros(1);e.age=torch.zeros(1);e.steps=900;e.failed=torch.zeros(1,dtype=torch.bool)
        e.dof=torch.zeros((1,28,2));e.rb=torch.zeros((1,1,13));e.object_index=0;e.stage_slider_start=torch.zeros(1);e.entry_frames=torch.zeros(1);e.best_entry_dwell=torch.zeros(1);e.entry_awarded=torch.zeros(1,dtype=torch.bool);e.held_frames=torch.zeros(1);e.max_held_frames=torch.zeros(1);e.best_entry_error=torch.ones(1)*float('inf');e.previous_potential=torch.ones(1)*.5;e.last=torch.zeros((1,27));e.failure_penalty=60.
        e.servo=lambda q:setattr(e,'command_target',q.clone());e.observation=lambda:torch.zeros((1,168))
        e.entry_metrics=lambda:dict(held=torch.ones(1,dtype=torch.bool),finite=torch.ones(1,dtype=torch.bool),clearance_m=torch.ones(1)*.03,error=torch.ones(1),potential=torch.ones(1)*.5,cap_distance_m=torch.ones(1)*.01)
        step=method('scripts/wuji_fresh_prefix_learning.py','FreshPrefixRegrasp','step');step(e,torch.tensor(p.action[None],dtype=torch.float32))
        np.testing.assert_allclose(e.command_target.numpy()[0],native,atol=1e-7);self.assertEqual(float(e.phase[0]),0.)
        # The new constraint uses actual H cache to end the episode with the
        # existing loss penalty; it never rewrites q/pose or gains.
        e.fail_on_self_contact=True;e.affordance_cache={'self_bad':torch.zeros(1,dtype=torch.bool)}
        _,safe_reward,safe_done,_=step(e,torch.zeros((1,27)));self.assertFalse(bool(safe_done[0]))
        e.affordance_cache['self_bad'][:]=True
        _,bad_reward,bad_done,_=step(e,torch.zeros((1,27)));self.assertTrue(bool(bad_done[0]));self.assertLess(float(bad_reward[0]),-59.)
        frozen=e.command_target.clone();step(e,torch.ones((1,27)));self.assertTrue(torch.equal(e.command_target,frozen))


    def test_v8_native_entry_uses_actual_pose_motion_over_reported_velocity(self):
        from scripts.wuji_pose_motion import PoseMotion
        class Box:pass
        class Kin:
            def forward(self,q):
                O=np.eye(4);O[2,3]=1.;return O
        class Hand:
            def forward(self,q):return {'hand_r_thumb_pad_link':np.eye(4)}
        p=Box();p.free_motor=True;p.incremental=True;p.pose_motion_observation=True;p.pose_motion=PoseMotion();p.warmed=False;p.slider_start=None;p.entry_dwell=0;p.entry_ready=False;p.spec={};p.kin=Kin();p.geometry=Box();p.geometry.w=Hand();p.geometry.knife_geometry=Box()
        g=p.geometry.knife_geometry;g.joint_xyz=np.zeros(3);g.joint_r=np.eye(3);g.axis=np.array([0,0,1.])
        p.pad_vertices=np.zeros((1,3));p.slider_half=np.ones(3)*.01;p.low=np.ones(27)*-2;p.high=np.ones(27)*2
        p.motor=np.zeros((2,27));p.correction=np.zeros(27);p.goal=np.array([0.,0.,0.,0.,0.,0.,1.]);p.goal_q=np.zeros(20);p.phase=0.;p.tick=1;p.episode_steps=900;p.action_period=15
        p.action=np.zeros(27);p.span=np.ones(27)*.6;p.slew=np.ones(27)*.006;p.offset=np.zeros(27);p.timing='free-motor-hold-v8';p.stream=io.StringIO()
        command=method('scripts/wuji_regrasp_reference_policy.py','RegraspReferencePolicy','command');O=Kin().forward(None)
        args=(p,O,np.zeros(27),np.zeros(27),np.zeros(27),np.zeros((0,3)),[])
        command(*args,object_velocity=np.ones(6)*1000,slider=0.,slider_velocity=0.)
        self.assertTrue(p.warmed);self.assertEqual(p.tick,1)
        command(*args,object_velocity=np.ones(6)*1000,slider=0.,slider_velocity=0.)
        self.assertEqual(p.entry_dwell,1);np.testing.assert_array_equal(p.pose_motion.velocity.numpy(),np.zeros(6))
        # Subsequent real translation must still reject motion, regardless of reported zero.
        O[0,3]=.1
        command(*args,object_velocity=np.zeros(6),slider=0.,slider_velocity=0.)
        self.assertEqual(p.entry_dwell,0);self.assertAlmostEqual(float(p.pose_motion.velocity[0]),3.,places=5)


    def test_actual_frame_dispatch_consumes_exact_noise_and_hands_off_once(self):
        from scripts.wuji_regrasp_contract import frame_window
        start=574/30;end=start+631/30
        calls=[i for i in range(1506) if frame_window(i*8/240,start,end)]
        self.assertEqual(calls,list(range(574,1205)))
        # One warm call, 630 actor calls, 42 held-action noise blocks.
        self.assertEqual((len(calls)-1)//15,42)
        self.assertTrue(frame_window(1205*8/240,end))
        for t in [end,np.nextafter(end,-np.inf),np.nextafter(end,np.inf)]:
            self.assertFalse(frame_window(t,start,end));self.assertTrue(frame_window(t,end))


if __name__=='__main__':unittest.main()
