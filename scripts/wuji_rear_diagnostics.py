"""Deployment-observable bounded diagnostic timing, shared by SDK and simulation."""
import numpy as np

def quintic(u):
    u=np.clip(u,0.,1.);return u**3*(10-15*u+6*u*u)

def reference_time(distance,stroke,duration):
    lo,hi=0.,1.
    for _ in range(50):
        mid=(lo+hi)/2
        if quintic(mid)<distance/stroke:lo=mid
        else:hi=mid
    return (lo+hi)/2*duration

class ShortProbe:
    def __init__(self,stroke,duration):
        self.start=reference_time(.004,stroke,duration)
        self.end=reference_time(.005,stroke,duration)
        self.brake_seconds=2*(self.end-self.start)
        self.finish=self.start+self.brake_seconds
    def clock(self,t):
        if t<=self.start:return float(t)
        if t>=self.finish:return self.end
        s=t-self.start;T=self.brake_seconds
        return self.start+s-s**3/T**2+.5*s**4/T**3
    def metadata(self):
        return dict(request_m=.005,full_prefix_until_m=.004,unchanged_full_goal=True,brake_start_s=self.start,reference_endpoint_s=self.end,brake_duration_s=self.brake_seconds,hold_start_s=self.finish,scope='Known reference clock only; does not read actual slider, contact or pose')

def local_response_target(anchor,joint,step,t,seconds):
    q=np.asarray(anchor).copy()
    # One second baseline, same bounded half sine as v1, one second recovery.
    age=t-1.
    if 0<age<seconds:q[joint]+=step*np.sin(np.pi*age/seconds)
    return q
