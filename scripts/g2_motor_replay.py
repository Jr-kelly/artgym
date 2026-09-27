"""Motor-only replay of an independently scored successful local trajectory.

This is an open-loop diagnostic baseline, not live teacher/student inference.
Never contains object poses to inject. Offsets are anchored once to the actual
handoff motor reference; original joint limits and command slew are mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def matrix(pose):
    out = np.eye(4)
    out[:3,:3] = Rotation.from_quat(pose[3:7]).as_matrix()
    out[:3,3] = pose[:3]
    return out


class MotorReplay:
    def __init__(self, path, actual_targets, lower, upper, contact_follow='none'):
        self.plan = json.loads(Path(path).read_text())
        self.offsets = np.asarray(self.plan['hand_target_offsets_rad'], dtype=np.float32)
        assert self.offsets.shape == (600,20)
        self.initial = np.asarray(actual_targets,dtype=np.float32).copy()
        self.lower, self.upper = np.asarray(lower), np.asarray(upper)
        self.previous = self.initial.copy()
        self.index = 0
        self.contact_follow = contact_follow
        self.correction = np.zeros(4)
        self.diagnostic = None
        if contact_follow != 'none':
            from scripts.wuji_kinematics import WujiKinematics
            self.fk = WujiKinematics()
            self.contact = self.plan['contact_reference']
            self.anchor = np.array(self.contact['anchor_local'])
        steps = np.diff(np.vstack([np.zeros((1,20)), self.offsets]),axis=0)
        assert np.max(np.abs(steps[:,:16])) < .020002
        assert np.max(np.abs(steps[:,16:])) < .025002
        intended = self.initial+self.offsets
        assert np.all(intended >= self.lower-1e-6) and np.all(intended <= self.upper+1e-6)

    def step(self, wrist=None, obj=None, slider=None):
        assert self.index < len(self.offsets)
        target = self.initial+self.offsets[self.index]
        if self.contact_follow != 'none':
            # Privileged motor-only feedback. The reference is the successful
            # sequence's commanded pad point relative to its ACTUAL slider.
            # Never interpret commanded penetration as a force measurement.
            relative = np.linalg.inv(matrix(obj))@matrix(wrist)
            def point(thumb):
                q = target.astype(float).copy();q[16:] = thumb
                frame = relative@self.fk.forward(q)[self.contact['link']]
                return frame[:3,:3]@self.anchor+frame[:3,3]
            nominal = target[16:].astype(float).copy()
            measured_point = point(nominal)
            desired = np.array(self.contact['command_points_in_slider'][self.index])
            desired[2] += float(slider)
            jacobian = np.column_stack([(point(nominal+np.eye(4)[j]*1e-4)-measured_point)/1e-4 for j in range(4)])
            error = desired-measured_point
            axes = [1] if self.contact_follow == 'normal' else [0,1,2]
            jacobian = jacobian[axes];error = error[axes]
            correction = jacobian.T@np.linalg.solve(jacobian@jacobian.T+np.eye(len(axes))*1e-6,error)
            wanted = np.clip(correction,-.08,.08)
            self.correction += np.clip(wanted-self.correction,-.2/30,.2/30)
            target[16:] += self.correction
            target[16:] = self.previous[16:]+np.clip(target[16:]-self.previous[16:],-.025,.025)
            target = np.clip(target,self.lower,self.upper).astype(np.float32)
            self.diagnostic = dict(mode=self.contact_follow,nominal_point_in_knife=measured_point.tolist(),
                desired_point_in_knife=desired.tolist(),correction_rad=self.correction.tolist(),
                clipped=bool(np.any(np.abs(correction)>.08)),
                source='live simulated knife and slider truth; command geometry, not measured force')
        self.last_increment = target-self.previous
        self.previous = target.copy()
        self.index += 1
        return target.copy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--score',type=Path,required=True)
    p.add_argument('--replica',type=int,required=True)
    p.add_argument('--contact-reference',action='store_true',help='Embed successful commanded pad point relative to actual source slider for a later explicitly privileged feedback diagnostic')
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    initial_path = Path(__file__).resolve().parents[1]/'configs/g2_local/S-actual-state.npz'
    initial = np.load(initial_path)
    t = np.load(a.trace)
    score = json.loads(a.score.read_text())['episodes'][a.replica]
    assert score['success'] and score['complete'] and len(t['time']) == 600
    offsets = t['reference_targets'][:,a.replica,7:27]-initial['reference_targets'][7:27]
    steps = np.diff(np.vstack([np.zeros((1,20)),offsets]),axis=0)
    plan = dict(method='open-loop replay of learned motor commands; not online teacher/student',
        source_trace=str(a.trace.resolve()),source_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),
        source_replica=a.replica,independent_source_score=score,
        reset_source_sha256=hashlib.sha256(initial_path.read_bytes()).hexdigest(),
        hand_order='index,middle,pinky,ring,thumb;4 joints each',
        seconds=20,control_hz=30,reversal_seconds=5,slider_goals_m=[.04,0,.04,0],
        reference='actual motor targets fixed once at takeover; no physical pose substitution',
        support_step_max_rad=float(np.max(np.abs(steps[:,:16]))),
        thumb_step_max_rad=float(np.max(np.abs(steps[:,16:]))),
        hand_target_offsets_rad=offsets.tolist())
    if a.contact_reference:
        from scripts.wuji_kinematics import WujiKinematics
        fk = WujiKinematics()
        geometry = json.loads((initial_path.parent/'thumb-material-path.json').read_text())
        anchor = np.array(geometry['anchor_local']);points = []
        for i in range(600):
            # Input at action time is the PRE-step state, not the result frame.
            obj = initial['object_rigid_state'] if i==0 else t['object_rigid_state'][i-1,a.replica]
            wrist = initial['wrist'] if i==0 else t['wrist'][i-1,a.replica]
            slider = float(initial['slider'] if i==0 else t['slider'][i-1,a.replica])
            frame = np.linalg.inv(matrix(obj))@matrix(wrist)@fk.forward(t['reference_targets'][i,a.replica,7:27])[geometry['contact_link']]
            point = frame[:3,:3]@anchor+frame[:3,3];point[2] -= slider
            points.append(point.tolist())
        plan['contact_reference'] = dict(link=geometry['contact_link'],anchor_local=anchor.tolist(),
            command_points_in_slider=points,scope='pre-step actual knife/wrist/slider; hypothetical commanded pad material point, not force or desired physical penetration',
            damping_m2=1e-6,correction_span_rad=.08,correction_slew_rad_s=.2)
    a.output.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({k:v for k,v in plan.items() if k not in ['hand_target_offsets_rad','contact_reference']}))


if __name__ == '__main__':main()
