"""Public-estimate contact-line family, recomputing the same static wrench preference.

All64 physical slots remain. Failed estimated IK falls back to the original
public-estimate planner by an explicit shared rule, never physical asset ID.
Static wrench failure retains the known bounded nominal-offset recipe and is
labelled; no successful initial states are filtered from training.
"""
import copy, json, os, pathlib, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.record_wuji_support_goal import record
from scripts.wuji_kinematics import WujiKinematics

R = pathlib.Path(__file__).resolve().parents[2]
D = R/'research/support-pressure-20261003'; OLD = R/'research/robust-knife-family-20261003'
B = R/'runs/support-pressure-20261003/contact-line-training-config-v66'
B.mkdir(parents=True, exist_ok=False)
scene = json.loads((D/'joint-looser-estimate-scene256-v32.json').read_text())
plan = json.loads((OLD/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text())
support = json.loads((D/'coordinated-preload-moderate-v6.json').read_text())
reference = json.loads((OLD/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text())
h = WujiKinematics()
record('contact_line_family_v66_preparation_started', evidence=str(B.relative_to(R)),
       config={'observation_bank':256, 'physical_slots':64, 'intended_thumb_bias_m':[-.002,0,0],
               'initial_observations':'Same synthetic larger-error bank v32; no new truth actor inputs'},
       next='Prepare all public-estimate plans, record each fallback, then short adaptation only')
begin = time.monotonic()


def one(item):
    i, original = item
    folder = B/('%04d'%i); folder.mkdir()
    estimate = original['estimate']
    motor, pressure, ref, audit = adapt(estimate, plan, support, reference, thumb_contact_bias_m=[-.002,0,0])
    ik_fallback = not ref['all_feasible'] or max(audit['contact_errors_m'].values()) >= .00025
    if ik_fallback:
        motor, pressure, ref, audit = adapt(estimate, plan, support, reference)
        assert ref['all_feasible'], 'Original public-estimate fallback also failed: '+str(i)
    (folder/'input-plan.json').write_text(json.dumps(motor, indent=2))
    cmd = [sys.executable, '-m', 'scripts.plan_g2_contact_equilibrium', '--plan', str(folder/'input-plan.json'),
        '--calibration', str(OLD/'functional-side-edge-under-support-v6/localization.json'),
        '--output', str(folder/'equilibrium'), '--thumb-normal', '1.5', '--closed-slider-passive-limit']
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with (folder/'planner.log').open('w') as log:
        result = subprocess.run(cmd, cwd=R, env=env, stdout=log, stderr=subprocess.STDOUT)
    wrench_fallback = result.returncode != 0
    if not wrench_fallback:
        motor = json.loads((folder/'equilibrium/motor-plan.json').read_text())
        touch = np.asarray(motor['touch_q'])
        pressure['post_lift_target_q'] = np.clip(touch+1.25*(np.asarray(motor['close_q'])-touch),
            h.lower+1e-4, h.upper-1e-4).tolist()
    ref['support_preload_schedule'] = dict(seconds=[12,14],
        delta_q=(np.asarray(pressure['post_lift_target_q'])-np.asarray(motor['close_q'])).tolist())
    audit.update(estimated_IK_fallback=ik_fallback, static_wrench_fallback=wrench_fallback,
        fallback_scope='Shared rule based only on public estimate/IK/static model; all physical slots retained',
        contact_bias_m=[0,0,0] if ik_fallback else [-.002,0,0])
    row = dict(estimate=estimate, motor_plan=motor, support_target_q=pressure['post_lift_target_q'],
               thumb_reference=ref, audit=audit)
    (folder/'planned-row.json').write_text(json.dumps(row, indent=2))
    return i, row


with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(one, enumerate(scene['initial_estimated_plans'])))
rows.sort(key=lambda pair:pair[0]); scene['initial_estimated_plans'] = [row for _,row in rows]
scene['contact_line_adaptation_scope'] = 'Fixed intended thumb-X bias -2mm relative to estimatedslidercenter, preserving all40mm stroke; estimated IK/static-wrench shared fallbacks labelled. No physicalID/currenttruth planner or actor inputs.'
out = D/'contact-line-estimate-scene256-v66.json'
out.write_text(json.dumps(scene, separators=(',',':')))
summary = dict(observations=len(rows), physical_slots=64, seconds=time.monotonic()-begin,
    estimated_IK_fallbacks=sum(row['audit']['estimated_IK_fallback'] for _,row in rows),
    static_wrench_fallbacks=sum(row['audit']['static_wrench_fallback'] for _,row in rows),
    max_path_error_m=max(row['audit']['trajectory_max_error_m'] for _,row in rows),
    scope='Offline estimated contact/wrench plans only; all physicalslots retained, no measured force/collision/success certification')
(D/'contact-line-family-preparation-v66-results.json').write_text(json.dumps(summary,indent=2))
record('contact_line_family_v66_preparation_closed', evidence=str(out.relative_to(R)), config=summary,
       conclusion='Full intended family prepared from public noisy estimates with labelled shared fallbacks, not physicaltruth selections.',
       next='Short same750-weight adaptation with ordinary/absorbing operation and ordinary learnedlift candidate; no long extension before actual behavior')
print(json.dumps(summary), flush=True)
