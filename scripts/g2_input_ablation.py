"""Frozen-policy input diagnostics; one ideal initial pose, no object feedback.

This is not a trained student. Body stationarity and pad no-slip are unverified
estimator assumptions. No simulator handle or state-writing API is available.
"""
import json
from pathlib import Path
from scripts.g2_local_env import local_pose  # Isaac Gym before torch
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics


class InputAblation:
    def __init__(self, mode, initial_object, initial_slider, initial_q):
        assert mode in ['fixed-body-live-slider','fixed-body-proprio-slider']
        self.mode=mode
        self.initial_object=initial_object[:,:7].clone()
        self.initial_slider=initial_slider.clone()
        self.arm=G2Kinematics();self.hand=WujiKinematics()
        plan=json.loads((Path(__file__).resolve().parents[1]/'configs/g2_local/thumb-material-path.json').read_text())
        self.anchor=np.array(plan['anchor_local']);self.link=plan['contact_link']
        self.axis=np.stack([Rotation.from_quat(o[3:7]).as_matrix()[:,2] for o in self.initial_object.numpy()])
        self.initial_points=self.kinematics(initial_q.numpy())[1]
        self.previous_slider=initial_slider.clone()
        self.estimated_slider=initial_slider.clone()

    def kinematics(self, q):
        wrists=[];points=[]
        for row in q:
            wrist=self.arm.forward(row[:7]);pad=wrist@self.hand.forward(row[7:27])[self.link]
            wrists.append(np.r_[wrist[:3,3],Rotation.from_matrix(wrist[:3,:3]).as_quat()])
            points.append(pad[:3,:3]@self.anchor+pad[:3,3])
        return np.asarray(wrists),np.asarray(points)

    def observation(self, q, qd, targets, age, residual, previous_action,
                    goals, lower, upper, slider_lower, live_slider=None, live_slider_velocity=None):
        # q/qd contain robot joints ONLY: no slider joint may enter FK/state.
        assert q.shape[1]==qd.shape[1]==27
        wrist,points=self.kinematics(q.numpy())
        # Frozen checkpoint's documented legacy representation: reset-frame
        # wrist dominant component positive, subsequent PhysX branch negative.
        # Pure convention, no current object or wrist truth needed.
        for i in range(len(wrist)):
            quat=wrist[i,3:7];positive=quat[np.argmax(np.abs(quat))]>0
            if positive != (int(age[i])==0):wrist[i,3:7]*=-1
        wrist=torch.tensor(wrist,dtype=torch.float32)
        local=local_pose(wrist,self.initial_object)
        if self.mode=='fixed-body-live-slider':
            assert live_slider is not None and live_slider_velocity is not None
            slider=live_slider;velocity=live_slider_velocity
        else:
            assert live_slider is None and live_slider_velocity is None
            slider=self.initial_slider+torch.tensor(np.sum((points-self.initial_points)*self.axis,axis=-1),dtype=torch.float32)
            velocity=(slider-self.previous_slider)*30
            velocity=torch.where(age==0,torch.zeros_like(velocity),velocity)
        self.previous_slider=slider.clone();self.estimated_slider=slider.clone()
        hand=q[:,7:27]
        qn=2*(hand-lower[7:27])/(upper[7:27]-lower[7:27])-1
        zeros=torch.zeros(len(q),3)
        return torch.cat((qn,qd[:,7:27]*.1,(targets[:,7:27]-hand)*5,
            zeros,zeros,local[:,:3]*10,local[:,3:7],zeros,zeros,
            (slider[:,None]-slider_lower)*25,velocity[:,None]*10,
            (goals[:,None]-slider_lower)*25,(goals-slider)[:,None]*25,
            age.float()[:,None]/600,residual/.20,previous_action),-1).clamp(-20,20)

    def description(self):
        return dict(mode=self.mode,scope='frozen joint policy input ablation, not trained student',
            ideal_initialization='one measured simulation object pose and slider value at reset/takeover',
            live_inputs='robot27 q/qd, command targets, clock, previous actions/residuals; URDF FK wrist',
            remaining_live_privilege='slider position/velocity' if self.mode=='fixed-body-live-slider' else None,
            body_assumption='fixed at initial world pose, zero linear/angular velocity',
            slider_assumption='same thumb pad material point, no slip, displacement projected onto initial knife axis',
            deployable=False,reason='ideal initialization and contact estimator not validated on hardware')
