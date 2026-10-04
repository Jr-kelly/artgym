"""Finite signed joint-tracking search with paused causal verification.

Measured joints and the independently issued previous motor target only. Lag
can reflect contact, friction or model error; it is not measured normal force.
No current object/contact/load input or solver state writes are permitted.
"""
from collections import deque
import numpy as np
class JointDeflectionAcquisition:
    def __init__(self,specification,initial):
        self.spec=specification;assert specification['all_requested_corridor_passed'];self.index=specification['hand_index'];self.sign=specification['inward_motor_sign'];assert 0<=self.index<16 and self.sign in [-1,1];self.start,self.end=specification['search_interval_seconds'];assert 12<=self.start<self.end<=16-50/30;self.anchor=float(initial[self.index]);assert abs(self.anchor-specification['anchor_rad'])<1e-6;self.target=self.anchor;self.offset=0.;self.lag=0.;self.state='waiting';self.values=deque(maxlen=specification['filter_frames']);self.confirm_frames=0;self.confirm_positive=0
    def command(self,time_s,measured,previous_issued,nominal):
        result=nominal.copy()
        if time_s<self.start:return result
        self.values.append(self.sign*float(previous_issued[self.index]-measured[self.index]));self.lag=float(np.mean(self.values))
        if time_s>=self.end:
            if self.state not in ['holding','bound']:self.state='timeout'
        elif self.state in ['waiting','searching']:
            self.state='searching'
            if len(self.values)==self.values.maxlen and self.lag>=self.spec['tracking_lag_threshold_rad']:
                self.state='verifying';self.confirm_frames=0;self.confirm_positive=0
            else:
                self.offset=min(self.spec['maximum_motor_offset_rad'],self.offset+self.spec['motor_step_rad']);self.target=self.anchor+self.sign*self.offset
                if self.offset>=self.spec['maximum_motor_offset_rad']-1e-8:self.state='bound'
        elif self.state=='verifying':
            self.confirm_frames+=1
            if self.confirm_frames>=self.spec['filter_frames']:self.confirm_positive=self.confirm_positive+1 if self.lag>=self.spec['tracking_lag_threshold_rad'] else 0
            if self.confirm_positive>=self.spec['consecutive_proxy_frames']:self.state='holding'
            elif self.confirm_frames>=self.spec['filter_frames']+self.spec['consecutive_proxy_frames']:self.state='searching'
        result[self.index]=self.target;return result
    def report(self):return dict(state=self.state,hand_index=self.index,target_rad=self.target,offset_rad=self.offset,filtered_signed_issued_minus_measured_rad=self.lag,specification=self.spec,scope=__doc__)
