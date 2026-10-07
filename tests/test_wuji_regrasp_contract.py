"""Exercise real caller methods without creating or stepping a simulator."""
import ast
import io
import json
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


if __name__=='__main__':unittest.main()
