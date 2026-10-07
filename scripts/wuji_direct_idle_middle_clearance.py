"""Small motor corrections for the unloaded middle during thumb transfer.

Uses measured joints, issued-target lag and explicit object pose. This is a
target clearance guard, not an actual continuous collision certificate.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics


class DirectIdleMiddleClearance:
    def __init__(self, spec, output):
        self.s=spec;self.k=G2Kinematics()
        self.g=DigitGeometry(max_face_axes=10,knife_spec=Path(spec['knife_spec']))
        self.log=Path(output)/'direct-idle-middle-clearance.jsonl'

    def correct(self,t,O,arm,hand,issued_arm,issued_hand,reference_arm,reference_hand,slider):
        if t<self.s['start_s']:return reference_hand
        predicted_wrist=self.k.forward(arm)@np.linalg.inv(self.k.forward(issued_arm))@self.k.forward(reference_arm)
        L=np.linalg.inv(O)@predicted_wrist
        lag=hand-issued_hand
        preferred=reference_hand[4:8].copy();margin=.06
        lo=self.g.w.lower[4:8]+margin;hi=self.g.w.upper[4:8]-margin
        clearance_m=self.s.get('clearance_m',.0008)

        def clear(x):
            q=reference_hand.copy()+lag;q[4:8]=x+lag[4:8]
            values=[v['gap_lower_bound_m']-clearance_m for v in self.g.gaps(q,L,slider,'middle')]
            values.extend(v['gap_lower_bound_m']-clearance_m for v in self.g.self_gaps(q,'middle',certify_clearance_m=clearance_m))
            return np.array(values)

        seed=np.clip(preferred,lo,hi);before=float(clear(seed).min());candidate=seed;solver_success=None
        if before<0:
            fit=minimize(lambda x:float(np.sum((x-preferred)**2)),seed,method='SLSQP',
                bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=clear)],
                options=dict(maxiter=40,ftol=1e-11))
            candidate=fit.x;solver_success=bool(fit.success)
        maximum=self.s.get('max_correction_rad',.15)
        candidate=preferred+np.clip(candidate-preferred,-maximum,maximum)
        after=float(clear(candidate).min());rejected_worse=after<before-1e-9
        if rejected_worse:candidate=seed;after=before
        out=reference_hand.copy();out[4:8]=candidate
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t),minimum_predicted_clearance_error_m=before,
                corrected_predicted_clearance_error_m=after,solver_success=solver_success,rejected_worse_correction=rejected_worse,
                correction_rad=(candidate-preferred).tolist(),issued_middle_q=candidate.tolist(),
                pose_source='sim_oracle explicit pose, measured joint/target lag',
                scope='Middle scheduled after actual supporthandoff; no nativecontact feedback; physicalcollision/PD/effort unchanged, actualchecks stillrequired'))+'\n')
        return out
