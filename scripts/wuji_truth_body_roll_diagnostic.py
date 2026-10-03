"""Non-deployable, single native diagnostic using actual knife orientation.

Only this diagnostic receives body truth. Motor corrections remain bounded by
the original issued support action span; no object force, attachment or reset.
It tests whether support coordination has physical authority to counter roll.
It is not exported as a deployable state estimator or counted as a demo.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics


class TruthBodyRollDiagnostic:
    def __init__(self, initial_object_in_wrist, gain=.35):
        self.g = DigitGeometry(); self.h = self.g.w; self.kin = G2Kinematics()
        self.initial = np.asarray(initial_object_in_wrist, dtype=float)
        self.gain = gain; self.reference = None
        self.last_error_rad = float('nan'); self.last_offset = np.zeros(20)
        self.vertices = {f:np.concatenate([v for v, _ in self.g.meshes['hand_r_'+f+'_pad_link']])
                         for f in ['index','middle','pinky']}
        self.normal = -self.initial[:3,1]

    def point(self, q, finger):
        t = self.h.forward(q)['hand_r_'+finger+'_pad_link']
        v = self.vertices[finger] @ t[:3,:3].T + t[:3,3]
        proj = v @ self.normal
        weights = np.exp(-(proj-proj.min())/.0002); weights /= weights.sum()
        return weights @ v

    def correction(self, measured_hand_q, measured_arm_q, actual_body_quaternion):
        wrist = self.kin.forward(measured_arm_q)
        relative = wrist[:3,:3].T @ Rotation.from_quat(actual_body_quaternion).as_matrix()
        if self.reference is None: self.reference = relative.copy()
        # Actual orientation is the deliberately privileged diagnostic signal.
        error = Rotation.from_matrix(self.reference.T @ relative).as_rotvec()[2]
        self.last_error_rad = float(error)
        rotate = Rotation.from_rotvec(-self.gain*error*self.reference[:,2]).as_matrix()
        q = np.asarray(measured_hand_q); result = np.zeros(20)
        for finger in ['index','middle','pinky']:
            ids = [self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)]
            point = self.point(q, finger)
            delta = (rotate-np.eye(3)) @ (point-self.initial[:3,3])
            jac = np.empty((3,4))
            for column, index in enumerate(ids):
                step = np.zeros(20); step[index] = 1e-5
                jac[:,column] = (self.point(q+step,finger)-self.point(q-step,finger))/2e-5
            offset = jac.T @ np.linalg.solve(jac @ jac.T+np.eye(3)*1e-6, delta)
            result[ids] = np.clip(offset,-.04,.04)
        self.last_offset = result
        return result.copy()
