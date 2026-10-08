"""One legal-input control core, shared by simulation and SDK IPC backends."""
import isaacgym # Import before torch, without changing the SDK Python environment.
import hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from scripts.wuji_goal_common import configuration
from scripts.g2_r800_policy import G2R800Policy
from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure
ROOT=Path(__file__).resolve().parents[1]
def load_bundle(path):
    s=json.loads(Path(path).read_text())
    if s['format']!='wuji-rear-bundle-v1':raise ValueError('Unknown bundle contract')
    for p,sha in s['required_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha:raise ValueError('Pinned dependency changed: '+p)
    return s
class RearController:
    def __init__(self,spec,pressure_enabled=True,estimate_delta_m=None):
        self.spec=spec
        cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
        self.cfg=cfg;self.policy=G2R800Policy(cfg,ROOT/spec['teacher'],ROOT/spec['student'],geometry=spec['geometry_estimate'],residual_checkpoint=ROOT/spec['residual'],thumb_reference_override=ROOT/spec['reference'])
        self.object_est=np.array(spec['object_initial_estimate']);self.slider_est=np.array(spec['slider_initial_estimate'])
        if estimate_delta_m is not None:
            delta=self.object_est[:3,:3]@np.asarray(estimate_delta_m);self.object_est[:3,3]+=delta;self.slider_est[:3,3]+=delta
        if pressure_enabled:
            self.policy.pressure_adapter=NativeJointDeflectionPressure(json.loads((ROOT/spec['pressure']).read_text()),self.object_est[:3,1],np.asarray(cfg.hand.dof_props.stiffness))
            self.policy.pressure_adapter.model.axial[0]=torch.as_tensor(self.object_est[:3,2],dtype=torch.float32)
        self.lower=np.asarray(spec['model_lower_rad']);self.upper=np.asarray(spec['model_upper_rad'])
        self.issued=None;self.last_action=np.zeros(20,dtype=np.float32);self.taken=False;self.pending=None;self.warmup=None
        self.latencies=[];self.gravity=np.asarray(spec['wrist_world'])[:3,:3].T@np.array([0,0,-1.])
    def observe(self,q):
        q=np.asarray(q,dtype=np.float64)
        if q.shape!=(20,) or not np.isfinite(q).all():raise ValueError('Invalid encoder sample')
        self.policy.record(q,self.last_action)
    def seed_issued(self,q):
        # The first command is measured current posture; no assumed device target.
        self.issued=np.asarray(q).copy()
    def propose_hold(self,desired):
        self.pending=dict(previous=self.issued.copy(),baseline=np.asarray(desired).copy(),policy=False)
        return np.asarray(desired).copy()
    def takeover(self,q):
        if len(self.policy.history)!=50:raise ValueError('Fifty new measured frames required')
        self.policy.takeover_estimate(q,self.issued,self.object_est,self.slider_est,clock_s=16.)
        self.warmup=self.policy.prewarm(q,self.spec['stroke_m'],self.gravity,iterations=8,clock_s=16.)
        self.taken=True
    def propose_push(self,q,elapsed_s):
        if not self.taken:self.takeover(q)
        previous=self.issued.copy();begin=time.perf_counter()
        ref=self.policy.thumb_reference
        complete=(float(ref.age[0])*ref.dt>=ref.duration+1/30-1e-7) if ref.pacing else elapsed_s>=ref.duration+1/30-1e-7
        target,_=self.policy.command(q,self.spec['stroke_m'],wrist_gravity=self.gravity,clock_s=16.+elapsed_s,issued_target_hold=complete)
        if torch.cuda.is_available():torch.cuda.synchronize()
        self.latencies.append((time.perf_counter()-begin)*1000)
        self.pending=dict(previous=previous,baseline=target.copy(),policy=True)
        return target
    def constrain(self,raw,device_lower=None,device_upper=None):
        reserve=float(self.spec.get("issued_limit_reserve_rad",0.))
        lo=self.lower+reserve if device_lower is None else np.maximum(self.lower+reserve,np.asarray(device_lower)+reserve)
        hi=self.upper-reserve if device_upper is None else np.minimum(self.upper-reserve,np.asarray(device_upper)-reserve)
        if np.any(lo>=hi):raise ValueError('Device and model limits do not overlap')
        # Same 30Hz, at most 0.025 radians per issue; model normalization unchanged.
        inside=np.all(self.issued>=lo-1e-6) and np.all(self.issued<=hi+1e-6)
        if self.taken and not inside:raise ValueError('Policy takeover outside model/device command range')
        desired=np.clip(raw,lo,hi)
        # A current device pose may lie outside the model corridor: approach it
        # gradually before takeover rather than jumping to the model boundary.
        return np.clip(desired,self.issued-.025,self.issued+.025)
    def commit(self,sent):
        if self.pending is None:raise RuntimeError('No pending command')
        sent=np.asarray(sent).copy();prev=self.pending['previous']
        if self.pending['policy']:
            p=self.policy;anchor=p.known.initial if p.known.support_anchor is None else p.known.support_anchor
            action=(sent-anchor[0].cpu().numpy())/p.known.support_span;action[16:]=(sent[16:]-prev[16:])/.025
            p.known.issued=p.tensor(sent);p.known.last_executed_action=p.tensor(action)
            if p.pressure_adapter is not None:
                m=p.pressure_adapter.model;m.offset[0]+=torch.as_tensor(sent[16:]-self.pending['baseline'][16:],dtype=torch.float32)
            p.last_action=action.astype(np.float32);self.last_action=p.last_action.copy()
        else:
            # Preparation: equivalent actually issued incremental actions, never raw targets.
            self.last_action=((sent-prev)/.025).astype(np.float32)
        self.issued=sent;self.pending=None
    def summary(self):
        a=np.asarray(self.latencies)
        return dict(measured_history_frames=len(self.policy.history),warmup=self.warmup,inference_ms_p50=float(np.median(a)) if len(a) else None,inference_ms_p95=float(np.quantile(a,.95)) if len(a) else None,inference_ms_max=float(a.max()) if len(a) else None,pressure_proxy_enabled=self.policy.pressure_adapter is not None,control_hz=30,normalization='Pinned model limits; separately intersect device limits for sending',inputs='Encoder q, FK, actual issued commands/actions history, fixed initial estimate and known wrist gravity only')
