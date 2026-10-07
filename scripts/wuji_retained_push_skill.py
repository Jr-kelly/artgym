"""Live entry to the retained new-knife push, with episode-local memory.

Original actor, reference, pressure model and known controller are used. Only
the stage clock and initial pose coordinates are adapted. No saved physical or
controller states from successful recordings are assigned to this episode.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure

ACTOR_SHA='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e'


class RetainedPushSkill:
    def __init__(self,cfg,spec,output):
        self.spec=spec;self.output=Path(output);self.start=float(spec['start_s'])
        self.settle=float(spec.get('preparation_seconds',4.))
        assert self.settle>=4.,'Retain pressure preparation plus 50 actual frozen history frames'
        checkpoint=Path('runs/newknife-20261005/train/center-tail-constant-motor-v1/update_000100.pth')
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==ACTOR_SHA
        self.policy=G2R800Policy(cfg,'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',
                                'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',
                                geometry=[.019,.008,.144,.007,.002,.032],residual_checkpoint=checkpoint,
                                thumb_reference_override='runs/contact-transfer-20261006/regression/nominal-125-video-v1/reference-control.json')
        self.pressure=json.loads(Path('runs/newknife-20261005/configs/pressure120.json').read_text())
        self.kin=G2Kinematics();self.knife=KnifeGeometry(spec['knife_spec'])
        self.entered=False;self.taken=False;self.previous_issued=None;self.anchor=None
        self.stream=(self.output/'retained-push-call.jsonl').open('w',buffering=1)

    def command(self,t,object_world,arm_q,q,issued_arm,issued_hand,slider):
        assert t>=self.start-1e-7
        vertices=np.concatenate([p['vertices'] for p in self.knife.collision_parts(slider)])
        clearance=float((vertices@object_world[:3,:3].T+object_world[:3,3])[:,2].min()-.75)
        if clearance<.002:
            raise RuntimeError('Retained push intake rejected: actual knife is still supported by the table or prior transition lost carrying')
        if not self.entered:
            self.entered=True;self.arm_target=np.array(issued_arm).copy();self.hand_target=np.array(issued_hand).copy()
            self.fixed_world_normal=object_world[:3,1].copy()
            normal=self.kin.forward(arm_q)[:3,:3].T@self.fixed_world_normal
            self.policy.pressure_adapter=NativeJointDeflectionPressure(self.pressure,normal,np.asarray(self.policy.cfg.hand.dof_props.stiffness))
            self.anchor=np.asarray(issued_hand).copy()
        elapsed=t-self.start
        clock=12.+elapsed if not self.taken else 16.+elapsed-self.settle
        self.policy.pressure_adapter.normal=self.kin.forward(arm_q)[:3,:3].T@self.fixed_world_normal
        if self.taken:
            self.policy.record(q,self.policy.last_action)
        else:
            action=np.zeros(20)
            action[:16]=(np.asarray(issued_hand)[:16]-self.anchor[:16])/.04
            if self.previous_issued is not None:action[16:]=(np.asarray(issued_hand)[16:]-self.previous_issued[16:])/.025
            self.policy.record(q,action)
        self.previous_issued=np.asarray(issued_hand).copy()
        if elapsed<self.settle-1e-7:
            hand=self.policy.pressure_adapter.command(q,issued_hand,self.hand_target,clock)
            self.stream.write(json.dumps({'time_s':t,'phase':'pressure-preparation','history_frames':len(self.policy.history)})+'\n')
            return self.arm_target.copy(),hand
        if not self.taken:
            W=self.kin.forward(arm_q);relative=np.linalg.inv(W)@object_world
            cap=object_world.copy();cap[:3,:3]=object_world[:3,:3]@self.knife.joint_r
            cap[:3,3]=object_world[:3,3]+object_world[:3,:3]@(self.knife.joint_xyz+self.knife.joint_r@self.knife.axis*slider)
            self.policy.takeover_estimate(q,issued_hand,relative,np.linalg.inv(W)@cap,clock_s=16.)
            self.taken=True;self.push_slider_start=float(slider)
            receipt={'time_s':t,'object_in_wrist':relative.tolist(),'hand_q':np.asarray(q).tolist(),
                     'issued_hand_target':np.asarray(issued_hand).tolist(),'slider_start_m':float(slider),
                     'history_frames':len(self.policy.history),'actor_sha256':ACTOR_SHA,
                     'scope':'Current episode sim_oracle pose and current measured history; no recorded success-state assignment'}
            (self.output/'retained-push-entry.json').write_text(json.dumps(receipt,indent=2))
        clock=16.+elapsed-self.settle
        hand,action=self.policy.command(q,.035,wrist_gravity=self.kin.forward(arm_q)[:3,:3].T@np.array([0.,0.,-1.]),clock_s=clock,
                                         issued_target_hold=clock-16>=self.policy.thumb_reference.duration+1/30-1e-7)
        self.stream.write(json.dumps({'time_s':t,'phase':'retained-push','original_clock_s':clock,
                                     'history_frames':len(self.policy.history),'slider_delta_m':float(slider)-self.push_slider_start,
                                     'max_action':float(np.max(abs(action)))})+'\n')
        return self.arm_target.copy(),hand
