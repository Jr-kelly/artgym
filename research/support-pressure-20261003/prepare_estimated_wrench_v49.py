"""Recompute static coordinated preload from the public estimated grip.

The original geometry adapter transports old nominal motor offsets. This
candidate recomputes their Jacobian/wrench balance at the new estimated touch
posture. Physical assets and live contact/object states are never read.
"""
import json,pathlib,subprocess,sys
import numpy as np
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_support_goal import record

R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003/pressure-config-v35';h=WujiKinematics()
for label in ['nominal','raised1']:
    folder=B/label/'estimated-wrench-v49';folder.mkdir(exist_ok=False)
    command=[sys.executable,'-m','scripts.plan_g2_contact_equilibrium','--plan',str(B/label/'motor-plan.json'),
             '--calibration','research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json',
             '--output',str(folder/'equilibrium'),'--thumb-normal','1.5','--closed-slider-passive-limit']
    with (folder/'planner.log').open('w') as log:subprocess.run(command,cwd=R,check=True,stdout=log,stderr=subprocess.STDOUT)
    fitted=json.loads((folder/'equilibrium/motor-plan.json').read_text());touch=np.asarray(fitted['touch_q'])
    target=np.clip(touch+1.25*(np.asarray(fitted['close_q'])-touch),h.lower+.0001,h.upper-.0001)
    spec=dict(post_lift_target_q=target.tolist(),ring_target_q=None,thumb_preload_delta_q=[0,0,0,0],transition_seconds=[12,14],
              scope='Publicnoisyestimatedgrip, recomputednominalstaticJacobian/wrench motorpreload; retainsoriginalcontacts/pickup/limits. No physicalasset/currentstate input, no measuredforce regulation.',
              nominal_static_wrench_audit=fitted['equilibrium_audit'])
    (folder/'support.json').write_text(json.dumps(spec,indent=2));print(label,fitted['equilibrium_audit']['normal_N'],flush=True)
record('estimated_geometry_static_wrench_targets_prepared',evidence='runs/support-pressure-20261003/pressure-config-v35/{nominal,raised1}/estimated-wrench-v49/support.json',
       conclusion='OriginalcommonIK preservesold nominalposition-offset vector atchanged geometry. Candidate recomputes finite staticwrench/Jacobian coordination fromsamepublicestimatedtouch pose, originalcontactlayout andforcepreference. Thisis stillmotorpreload/modelonly; physicalforce needsnativecheck.',
       next='Two actualfullTABLE trials, not a higherfixedpressure sweep or newphysicalasset/oracle controller')
