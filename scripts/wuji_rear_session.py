"""Small explicit loaded-session contract, shared by SDK and finite-actuator sim.
This module has no robot backend. G2 hardware support remains blocked separately.
"""
import time
import numpy as np

def smooth(u):
    u=np.clip(u,0,1)
    return u**3*(10-15*u+6*u*u)

class RearSession:
    def __init__(self,controller):
        self.c=controller;self.state='untrusted_restart';self.generation=0;self.slider_changed=False
    def confirm_empty(self):
        self.state='empty';self.slider_changed=False;self.generation+=1
    def begin_open(self):
        if self.state!='empty':raise RuntimeError('Unload knife before opening or restarting; measured q cannot recover loaded motor target')
        self.state='waiting_placement'
    def placed(self):
        if self.state!='waiting_placement':raise RuntimeError('Placement phase required')
        self.state='closing'
    def unsupported(self):
        if self.state!='closing':raise RuntimeError('Closing phase required')
        self.c.policy.history=[];self.state='loaded_hold'
    def response(self):
        if self.state!='loaded_hold' or self.slider_changed:raise RuntimeError('Response requires original loaded hold')
        self.state='response'
    def response_done(self):
        if self.state!='response':raise RuntimeError('Response phase required')
        self.state='analysis_hold'
    def prepare_push(self,operation):
        if self.state not in ['loaded_hold','analysis_hold'] or self.slider_changed:raise RuntimeError('Probe changed slider: unload, reset 30mm edge, replace, and recollect history before full push')
        if operation not in ['probe','push']:raise ValueError('Unknown rear operation')
        self.c.operation=operation
        if operation=='probe':
            from scripts.wuji_rear_diagnostics import ShortProbe
            self.c.probe=ShortProbe(self.c.spec['stroke_m'],self.c.policy.thumb_reference.duration)
        else:self.c.probe=None
        self.state='preparing_'+operation
    def push_done(self):
        if self.state not in ['preparing_probe','preparing_push']:raise RuntimeError('Push preparation required')
        self.slider_changed=True;self.state='post_push_hold'
    def wait_unload(self):
        if self.state not in ['loaded_hold','analysis_hold','post_push_hold']:raise RuntimeError('Loaded hold required before unload')
        self.state='waiting_unload'
    def unloaded(self):
        if self.state!='waiting_unload':raise RuntimeError('Explicit unload confirmation required')
        self.confirm_empty()
    def target(self,phase,q,t,start=None):
        """Exact existing command semantics; all issued targets committed by backend."""
        if phase=='close':
            if self.state!='closing':raise RuntimeError('Cannot close outside placement')
            opened=np.asarray(self.c.spec['open_q_rad']) if start is None else start
            return self.c.propose_hold(opened+smooth(t/self.c.spec['prepare_seconds'])*(np.asarray(self.c.spec['hold_target_rad'])-opened))
        if phase=='push':
            if self.state not in ['preparing_probe','preparing_push']:raise RuntimeError('Loaded push requires preparation')
            return self.c.propose_push(q,t)
        return self.c.propose_hold(self.c.issued)

class DeadlineLoop:
    """30Hz samples with no burst catch-up. Abort missed periods, log actual gap."""
    def __init__(self,clock=time.monotonic,sleep=time.sleep,hz=30):
        self.clock=clock;self.sleep=sleep;self.dt=1/hz;self.next=None;self.previous=None;self.last_gap=None
    def tick(self):
        now=self.clock()
        if self.next is None:self.next=now
        if now>self.next+self.dt:raise TimeoutError('Missed a full 30Hz period; no catch-up commands sent')
        self.sleep(max(0,self.next-now));now=self.clock()
        if now>self.next+self.dt:raise TimeoutError('Scheduler wakeup missed a full period')
        self.last_gap=None if self.previous is None else now-self.previous
        self.previous=now
        # If late, the next sample is at least one period later, never a burst.
        self.next=now+self.dt
        return now
    def rebase_after_pause(self):
        """Only an explicit isolated warmup/model-load pause; firmware target retained."""
        self.next=max(self.clock(),self.previous+self.dt) if self.previous is not None else self.clock()

class ExternalForceTail:
    """Bounded incremental JSONL read; never rescan an expanding force recording."""
    def __init__(self,path):self.path=path;self.offset=0;self.partial=b'';self.latest=None
    def sample(self):
        if self.path.stat().st_size<self.offset:raise ValueError('External force log was truncated')
        with self.path.open('rb') as f:
            f.seek(self.offset);block=f.read(65536);self.offset=f.tell()
        parts=(self.partial+block).split(b'\n');self.partial=parts.pop()
        if len(self.partial)>65536:raise ValueError('External force row exceeds bound')
        import json
        for line in parts:
            if not line.strip():continue
            v=json.loads(line)
            if v.get('axis') not in ['normal','axial'] or not np.isfinite(v['force_N']) or 'host_monotonic_ns' not in v or not v.get('source'):raise ValueError('Force log needs axis, N, monotonic timestamp, source')
            self.latest=v
        return None if self.latest is None else dict(self.latest,age_ns=time.monotonic_ns()-self.latest['host_monotonic_ns'],alignment_only=True)
