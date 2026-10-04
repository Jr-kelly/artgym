"""One native NumPy versus batched initial-prior coordinate comparison."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_initial_table_prior import measured_arm_relative
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004/strict-geometry-table-prior-prefix-v2')
s=json.loads((B/'scene16.json').read_text());t=np.load(B/'qualification/trace.npz');kin=G2Kinematics();results=[]
templates=s['initial_estimated_plans']
for i in range(len(templates)):
    # The scene resamples noisy templates at reset. Identify its selected known
    # reference from the logged public scheduled motor target, never object truth.
    errors=[float(np.max(abs(t['known_scheduled_support_reference'][450,i]-np.asarray(row['support_target_q'])))) for row in templates]
    selected=int(np.argmin(errors));assert errors[selected]<1e-6, errors
    row=templates[selected]
    poses=measured_arm_relative(row['motor_plan'],row['estimate'],kin.forward(t['arm_q'][149,i]))
    metrics={}
    for label,pose in zip(['object','slider'],poses):
        actual=t['initial_'+label+'_estimate'][150,i]
        rotation=Rotation.from_quat(actual[3:]).as_matrix()
        metrics[label]=dict(position_difference_m=float(np.linalg.norm(pose[:3,3]-actual[:3])),rotation_difference_rad=float(Rotation.from_matrix(pose[:3,:3].T@rotation).magnitude()))
    results.append(dict(env=i,selected_known_template=selected,scheduled_reference_difference_rad=errors[selected],**metrics))
report=dict(scope='Shared known-table/once-initial-estimate/measured-arm FK NumPy/native versus batched float32 comparison; no current object truth in expected pose',rows=results,max_position_difference_m=max(row[k]['position_difference_m'] for row in results for k in ['object','slider']),max_rotation_difference_rad=max(row[k]['rotation_difference_rad'] for row in results for k in ['object','slider']))
assert report['max_position_difference_m']<2e-6 and report['max_rotation_difference_rad']<2e-5,report
(B/'initial-prior-parity.json').write_text(json.dumps(report,indent=2));record('phase_correct_table_prior_native_batch_parity_verified',config=report,evidence=str(B/'initial-prior-parity.json'),next='Fixed50 paired learned-prefix behavior and legal offline replay; no truth pose correction')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
