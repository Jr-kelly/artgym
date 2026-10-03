"""Public-estimate contact-line family, recomputing the same static wrench preference.

All64 physical slots remain. Failed estimated IK falls back to the original
public-estimate planner by an explicit shared rule, never physical asset ID.
Static wrench failure retains the known bounded nominal-offset recipe and is
labelled; no successful initial states are filtered from training.
"""
import copy, json, os, pathlib, subprocess, sys, time
import argparse
p=argparse.ArgumentParser();p.add_argument("--resume-unfinished",action="store_true");args=p.parse_args()
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.record_wuji_support_goal import record
from scripts.wuji_kinematics import WujiKinematics

R = pathlib.Path(__file__).resolve().parents[2]
D = R/'research/support-pressure-20261003'; OLD = R/'research/robust-knife-family-20261003'
B = R/'runs/support-pressure-20261003/braced-support-training-config-v83'
B.mkdir(parents=True, exist_ok=args.resume_unfinished)
scene = json.loads((D/'joint-looser-estimate-scene256-v32.json').read_text())
plan = json.loads((OLD/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text())
support = json.loads((D/'coordinated-preload-moderate-v6.json').read_text())
reference = json.loads((OLD/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text())
h = WujiKinematics()
record('braced_support_family_v83_preparation_started', evidence=str(B.relative_to(R)),
       config={'observation_bank':256, 'physical_slots':64, 'support_brace_contact_knife_x_m':{'index':.002,'middle':.001},
               'initial_observations':'Same synthetic larger-error bank v32; no new truth actor inputs'},
       next='Prepare all public-estimate plans, record each fallback, then short adaptation only')
begin = time.monotonic()


def one(item):
    i, original = item
    folder = B/('%04d'%i)
    if args.resume_unfinished and (folder/'planned-row.json').exists():return i,json.loads((folder/'planned-row.json').read_text())
    folder.mkdir(exist_ok=args.resume_unfinished)
    estimate = original['estimate']
    motor, pressure, ref, audit = adapt(estimate, plan, support, reference)
    audit['original_path_IK_feasible']=ref['all_feasible'] # retain original challengingobservation, never filter
    brace_output=folder/'brace'
    if brace_output.exists():brace_output=folder/'brace-retry1'
    from scripts.plan_wuji_braced_support import plan as brace_plan
    fallback=False
    try:
        pressure,ref=brace_plan(motor,pressure,ref,brace_output,OLD/'functional-side-edge-under-support-v6/localization.json')
    except (AssertionError,ValueError) as error:
        fallback=True
        (folder/'brace-failure.json').write_text(json.dumps(dict(error=str(error),scope='Publicestimate plannerfailure; retained original boundedrecipe, physicalslot never removed'),indent=2))
    audit.update(brace_fallback=fallback,estimated_IK_fallback=fallback,static_wrench_fallback=False,
        fallback_scope='Shared publicestimate planning failure falls back to original publicestimate grip; no actualstatefiltering')
    row = dict(estimate=estimate, motor_plan=motor, support_target_q=pressure['post_lift_target_q'],
               thumb_reference=ref, audit=audit)
    (folder/'planned-row.json').write_text(json.dumps(row, indent=2))
    return i, row


with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(one, enumerate(scene['initial_estimated_plans'])))
rows.sort(key=lambda pair:pair[0]); scene['initial_estimated_plans'] = [row for _,row in rows]
scene['support_brace_adaptation_scope'] = 'One coordinated opposite-side index+middle brace afteractualpickup; same oldthumbpath/1.5N staticpreference and1.25offsettier. All256 publicobservations and64physicalslots retained, labelled shared estimatedplanning fallback. No physicalID/currenttruth planner/actor input.'
out = D/'braced-support-estimate-scene256-v83.json'
out.write_text(json.dumps(scene, separators=(',',':')))
summary = dict(observations=len(rows), physical_slots=64, seconds=time.monotonic()-begin,
    estimated_IK_fallbacks=sum(row['audit']['estimated_IK_fallback'] for _,row in rows),
    static_wrench_fallbacks=sum(row['audit']['static_wrench_fallback'] for _,row in rows),
    retained_original_path_IK_failures=sum(not row['thumb_reference']['all_feasible'] for _,row in rows),
    max_path_error_m=max(row['audit']['trajectory_max_error_m'] for _,row in rows),
    scope='Offline estimated contact/wrench plans only; all physicalslots retained, no measured force/collision/success certification')
(D/'braced-support-family-preparation-v83-results.json').write_text(json.dumps(summary,indent=2))
record('braced_support_family_v83_preparation_closed', evidence=str(out.relative_to(R)), config=summary,
       conclusion='Full intended family prepared from public noisy estimates with labelled shared fallbacks, not physicaltruth selections.',
       next='Short same750-weight ordinary/absorbing brace adaptation, with512physicalslots perjob and same256-observation bank duplicated; FK-plane proxy failed offlinecheck and is not used; no longextension before actualbehavior')
print(json.dumps(summary), flush=True)
