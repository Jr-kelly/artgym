"""Bounded measured-joint tracking of an opt-in free-space hand path.

This adjusts issued motor targets; the original physical PD, torque limits and
collisions remain unchanged. It is not used to prescribe bearing contact force.
"""
import json
from pathlib import Path
import numpy as np
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth


class DirectJointPathTracking:
    def __init__(self,spec,output):
        self.s=spec;self.ids=np.array(spec['joint_indices'],dtype=int)
        self.t=np.array([r['time_s'] for r in spec['path']])
        self.q=np.array([r['joint_q'] for r in spec['path']])
        if np.any(np.diff(self.t)<=0) or self.q.shape!=(len(self.t),len(self.ids)):
            raise ValueError('Joint path must have ordered times and matching columns')
        self.offset=np.zeros(len(self.ids));self.actual_delta=None
        self.h=WujiKinematics();self.log=Path(output)/'direct-joint-path-tracking.jsonl'

    def correct(self,t,hand,reference):
        if self.actual_delta is None:self.actual_delta=hand[self.ids]-self.q[0]
        desired=np.array([np.interp(t,self.t,self.q[:,j]) for j in range(len(self.ids))])+self.actual_delta
        error=desired-hand[self.ids]
        delta=np.clip(error*self.s['gain_per_frame']*smooth(t/self.s['activation_s']),
            -self.s['max_step_rad'],self.s['max_step_rad'])
        self.offset=np.clip(self.offset+delta,-self.s['max_correction_rad'],self.s['max_correction_rad'])
        command=reference.copy()
        command[self.ids]=np.clip(reference[self.ids]+self.offset,self.h.lower[self.ids],self.h.upper[self.ids])
        self.offset=command[self.ids]-reference[self.ids]
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t),joint_indices=self.ids.tolist(),
                desired_actual_q=desired.tolist(),measured_q=hand[self.ids].tolist(),
                tracking_error_rad=error.tolist(),motor_correction_rad=self.offset.tolist(),
                scope='Free-space measured-joint target tracking; original physical actuator/collision limits unchanged'))+'\n')
        return command
