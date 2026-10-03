"""Finite proprioceptive postlift support search, not a force controller.

Only measured joint7 and independently issued motor targets enter. A paused
verification period distinguishes static joint lag from motion/filter lag.
All changes end early enough for50 real constant-target frames before takeover.
"""
from collections import deque
import numpy as np


class MiddleDeflectionSupport:
    def __init__(self, specification, initial):
        self.spec=specification
        assert specification['all_requested_corridor_passed']
        self.start,self.end=specification['search_interval_seconds']
        assert 12<=self.start<self.end<=16-50/30
        self.index=specification['hand_index'];assert self.index==7
        self.target=float(initial[self.index])
        assert abs(self.target-specification['motor_upper_rad'])<1e-6
        self.values=deque(maxlen=specification['filter_frames'])
        self.lag=0.;self.state='waiting';self.confirm_frames=0;self.confirm_positive=0

    def command(self,time_s,measured,nominal):
        # Pair each observation with the target that actually produced it.
        # Filtering q first and subtracting the latest moving target creates
        # an artificial lag equal to the moving-average delay.
        self.values.append(float(measured[self.index])-self.target);self.lag=float(np.mean(self.values))
        threshold=self.spec['filtered_deflection_threshold_rad']
        if time_s<self.start:return nominal.copy()
        if time_s>=self.end:
            if self.state not in ['holding','timeout','bound']:self.state='timeout'
        elif self.state in ['waiting','searching']:
            self.state='searching'
            if self.lag>=threshold:
                self.state='verifying';self.confirm_frames=0;self.confirm_positive=0
            else:
                self.target=max(self.spec['motor_lower_rad'],self.target-self.spec['motor_step_rad'])
                if self.target<=self.spec['motor_lower_rad']+1e-8:self.state='bound'
        elif self.state=='verifying':
            self.confirm_frames+=1
            # Wait until moving-average history contains only paused commands.
            if self.confirm_frames>=self.spec['filter_frames']:
                self.confirm_positive=self.confirm_positive+1 if self.lag>=threshold else 0
            if self.confirm_positive>=self.spec['consecutive_contact_proxy_frames']:self.state='holding'
            elif self.confirm_frames>=self.spec['filter_frames']+self.spec['consecutive_contact_proxy_frames']:
                self.state='searching'
        output=nominal.copy();output[self.index]=self.target
        return output

    def report(self):
        return dict(state=self.state,target_rad=self.target,filtered_measured_minus_target_rad=self.lag,specification=self.spec,scope='Measuredjoint/knowncommand loadproxy only; actualknifecontact andsupport judgedseparately. Originalgains/effort/limits, no currentobject/contact truth, no constantforce claim.')


class BatchedMiddleDeflectionSupport:
    """Same finite measured-minus-issued-target algorithm on a Torch batch."""
    def __init__(self, specification, n, device):
        import torch
        self.torch=torch;self.spec=specification
        assert specification['all_requested_corridor_passed']
        self.start,self.end=specification['search_interval_seconds']
        assert 12<=self.start<self.end<=16-50/30 and specification['hand_index']==7
        self.target=torch.full((n,),specification['motor_upper_rad'],device=device)
        self.values=torch.zeros((n,specification['filter_frames']),device=device)
        self.count=torch.zeros(n,device=device,dtype=torch.long)
        self.state=self.count.clone();self.confirm_frames=self.count.clone();self.confirm_positive=self.count.clone()
        self.lag=self.target*0

    def reset(self, ids):
        self.target[ids]=self.spec['motor_upper_rad'];self.values[ids]=0;self.count[ids]=0
        self.state[ids]=0;self.confirm_frames[ids]=0;self.confirm_positive[ids]=0;self.lag[ids]=0

    def command(self, time_s, measured, nominal):
        t=self.torch;s=self.spec;active=(time_s>=self.start)&(time_s<16)
        values=t.roll(self.values[active],1,1);values[:,0]=measured[active,7]-self.target[active]
        self.values[active]=values;self.count[active]=(self.count[active]+1).clamp_max(s['filter_frames'])
        self.lag[active]=values.sum(1)/self.count[active].clamp_min(1)
        before=self.state.clone();threshold=s['filtered_deflection_threshold_rad']
        expired=active&(time_s>=self.end)&(before!=3)&(before!=4)&(before!=5)
        self.state[expired]=4
        search=active&(time_s<self.end)&((before==0)|(before==1))
        verify=search&(self.lag>=threshold);moving=search&~verify
        self.state[search]=1;self.state[verify]=2;self.confirm_frames[verify]=0;self.confirm_positive[verify]=0
        self.target[moving]=(self.target[moving]-s['motor_step_rad']).clamp_min(s['motor_lower_rad'])
        self.state[moving&(self.target<=s['motor_lower_rad']+1e-8)]=5
        paused=active&(time_s<self.end)&(before==2);self.confirm_frames[paused]+=1
        settled=paused&(self.confirm_frames>=s['filter_frames'])
        self.confirm_positive[settled]=t.where(self.lag[settled]>=threshold,self.confirm_positive[settled]+1,0)
        held=paused&(self.confirm_positive>=s['consecutive_contact_proxy_frames']);self.state[held]=3
        retry=paused&~held&(self.confirm_frames>=s['filter_frames']+s['consecutive_contact_proxy_frames']);self.state[retry]=1
        output=nominal.clone();output[active,7]=self.target[active];return output


class MiddleLoadLagRegulator:
    """Finite motor adjustment using a load proxy, never measured force.

    Runtime inputs are observed joint position and the previously issued target.
    The existing finite controller supplies the anchor; support adjustments stay
    within its original +/-0.04rad command span and certified held corridor.
    """
    def __init__(self, specification, initial_target):
        self.spec=specification;self.anchor=float(initial_target);self.target=self.anchor
        self.lower=max(specification['motor_lower_rad'],self.anchor-.04)
        self.upper=min(specification['motor_upper_rad'],self.anchor+.04,specification.get('operation_motor_upper_rad',self.anchor+.04))
        self.values=deque(maxlen=specification['filter_frames']);self.lag=0.;self.saturated_frames=0

    def command(self, measured, issued_target, nominal):
        self.values.append(float(measured[7])-float(issued_target[7]));self.lag=float(np.mean(self.values))
        if len(self.values)==self.values.maxlen:
            if self.lag>.028:self.target=min(self.upper,self.target+.001)
            elif self.lag<.018:self.target=max(self.lower,self.target-.001)
        self.saturated_frames+=int(self.target<=self.lower+1e-8 or self.target>=self.upper-1e-8)
        result=nominal.copy();result[7]=self.target;return result

    def report(self):
        return dict(anchor_rad=self.anchor,target_rad=self.target,bounds_rad=[self.lower,self.upper],filtered_observed_minus_issued_rad=self.lag,lag_band_rad=[.018,.028],maximum_motor_step_rad=.001,saturated_control_frames=self.saturated_frames,scope='Proprioceptive loadproxy deadband, not exact contactownership or constant/measured force. Originallimits/gains/gravity; no object/slider/contacttruth.')
