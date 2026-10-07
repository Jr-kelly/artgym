"""Geometry-aware thumb acquisition in the current explicit knife pose.

The arm and carrier motor references stay anchored. Only the thumb follows the
known cap acquisition path; native force/contact logs are evaluation-only.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth


class DirectRelativeThumbPath:
    def __init__(self,spec,output):
        self.s=spec;self.g=DigitGeometry(max_face_axes=8,knife_spec=Path(spec['knife_spec']))
        self.k=G2Kinematics();self.m=np.asarray(spec['material_point']);self.local=np.asarray(spec['material_normal_local'])
        self.times=np.asarray([r['time_s'] for r in spec['path']]);self.P=np.asarray([r['point_knife_m'] for r in spec['path']])
        self.N=np.asarray([r['normal_knife'] for r in spec['path']]);self.Q=np.asarray([r['thumb_q'] for r in spec['path']])
        self.kp=np.asarray(spec['thumb_kp']);self.kd=np.asarray(spec['thumb_kd']);self.previous=None;self.log=Path(output)/'direct-relative-thumb-path.jsonl'
        self.slider0=None;self.completed_at=None

    def correct(self,t,O,arm,hand,issued_hand,reference,slider):
        L=np.linalg.inv(O)@self.k.forward(arm);q=hand.astype(float);name='hand_r_thumb_pad_link'
        if self.slider0 is None:self.slider0=float(slider)
        query_time=t;progress=float(slider)-self.slider0
        if self.s.get('stroke_m') is not None:
            if progress>=self.s['completion_displacement_m'] and self.completed_at is None:self.completed_at=float(t)
            lead=self.s['slider_lead_m']*smooth((t-self.s['stroke_start_s'])/self.s['axial_ramp_s'])
            if self.completed_at is not None:lead*=1-smooth((t-self.completed_at)/self.s['hold_ramp_s'])
            shift=np.clip(max(0.,progress)+lead,0.,self.s['stroke_m'])
            query_time=self.times[0]+(self.times[-1]-self.times[0])*shift/self.s['stroke_m']
        target=np.array([np.interp(query_time,self.times,self.P[:,j]) for j in range(3)])
        normal=np.array([np.interp(query_time,self.times,self.N[:,j]) for j in range(3)]);normal/=np.linalg.norm(normal)
        prior=np.array([np.interp(query_time,self.times,self.Q[:,j]) for j in range(4)])
        if self.previous is None:self.previous=q[16:].copy();self.source_deformation=issued_hand[16:]-q[16:];self.last_time=t
        margin=self.s.get('planning_margin_rad',.04)
        lo=self.g.w.lower[16:]+margin;hi=self.g.w.upper[16:]-margin
        lo=np.maximum(lo,self.previous-.12);hi=np.minimum(hi,self.previous+.12)
        def point(h):
            T=L@self.g.w.forward(h)[name];return T[:3,:3]@self.m+T[:3,3]
        def residual(x):
            h=q.copy();h[16:]=x;F=self.g.w.forward(h);T=L@F[name];r=list((T[:3,:3]@self.m+T[:3,3]-target)*500)
            r.extend((T[:3,:3]@self.local-normal)*.15);r.extend((x-prior)*.015)
            for v in self.g.gaps(h,L,slider,'thumb',frames=F):
                threshold=-.00025 if v['hand_link']==name and v['knife_link']=='link_1' else .0004
                r.append(min(0,v['gap_lower_bound_m']-threshold)*700)
            r.extend(min(0,v['gap_lower_bound_m']-.0002)*200 for v in self.g.self_gaps(h,'thumb',certify_clearance_m=.0002,frames=F))
            return np.asarray(r)
        fit=least_squares(residual,np.clip(self.previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=18,diff_step=1e-5)
        h=q.copy();h[16:]=fit.x;P=point(h);J=np.empty((3,4))
        for j in range(4):
            hh=h.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)-P)/1e-5
        force=np.array([0.,-self.s['normal_reference_N'],0.])*smooth((t-self.s['pressure_start_s'])/self.s['pressure_ramp_s'])
        if self.s.get('stroke_m') is not None:
            force[2]=self.s['axial_reference_N']*smooth((t-self.s['stroke_start_s'])/self.s['axial_ramp_s'])
            if self.completed_at is not None:force[2]*=1-smooth((t-self.completed_at)/self.s['hold_ramp_s'])
        offset=self.source_deformation*(1-smooth(t/self.s['release_s']))+np.clip(J.T@force/self.kp,-.12,.12)
        lead=np.zeros(4)
        if t>self.last_time:lead=np.clip(self.kd/self.kp*(fit.x-self.previous)/(t-self.last_time),-.07,.07)
        command=reference.copy();command[16:]=np.clip(fit.x+offset+lead,self.g.w.lower[16:]+.035,self.g.w.upper[16:]-.035)
        if t==0:command[16:]=issued_hand[16:]
        self.previous=fit.x.copy();self.last_time=t
        with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),target_knife_m=target.tolist(),fitted_point_knife_m=P.tolist(),
            measured_point_knife_m=point(q).tolist(),fit_error_m=float(np.linalg.norm(P-target)),fitted_thumb_q=fit.x.tolist(),
            active_slider_displacement_m=progress,completed_at_s=self.completed_at,
            motor_thumb_q=command[16:].tolist(),pose_source='sim_oracle currentknife, measuredjoints and issuedhistory',scope=__doc__))+'\n')
        return command
