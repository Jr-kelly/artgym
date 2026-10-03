"""Simulation once-initial observation generation, then the common public IK.

Physical parameters are read ONLY to synthesize a labelled noisy sensor sample.
The planner accepts that sample, never the parameters/instance ID. Observations
are fixed per environment for this short pilot; episodes still randomize pose,
sensor bias/noise, material, load and latency. This is not connected real vision.
"""
import json,pathlib,numpy as np
from scripts.plan_wuji_initial_geometry import adapt
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/support-pressure-20261003';old=R/'research/robust-knife-family-20261003'
schedule=json.loads((D/'bounded-offset-pilot-geometry-v1.json').read_text());rng=np.random.default_rng(2026100373)
plan=json.loads((old/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text())
support=json.loads((D/'coordinated-preload-moderate-v6.json').read_text());reference=json.loads((old/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text());records=[]
for i,instance in enumerate(schedule['instances']):
    truth=json.loads((R/'assets/objects/knife_wuji_dense_under_20261003'/instance/'parameters.json').read_text())
    observed_size=np.asarray(truth['handle_size'])+rng.uniform(-1,1,3)*np.array([.00025,.00025,.0005])
    relative_slider=np.asarray(truth['slider_origin'])-np.array([0,.0075,.010624586881962734])
    relative_slider[1]-=(truth['handle_size'][1]-.012)/2
    observed_slider=relative_slider+rng.uniform(-.00025,.00025,3)
    estimate=dict(handle_size_WTL_m=observed_size.tolist(),slider_contact_shift_m=observed_slider.tolist(),initial_object_center_shift_knife_m=[0,float((observed_size[1]-.012)/2),0],uncertainty_m=.00025,source='Synthetic noisy once-initial observation: W/T +/-0.25mm,L +/-0.5mm,sliderXYZ +/-0.25mm; physicalmetadata used only for simulated sensor generation, not planner/actor input; no connected realvision.')
    motor,pressure,thumb,audit=adapt(estimate,plan,support,reference)
    records.append(dict(estimate=estimate,motor_plan={k:motor[k] for k in ['open_q','touch_q','close_q','close_waypoints']},support_target_q=pressure['post_lift_target_q'],thumb_reference=thumb,audit=audit))
    if (i+1)%32==0:print(json.dumps({'prepared':i+1,'total':len(schedule['instances'])}),flush=True)
scene=dict(scope='Initial noisy estimate guided common motor planning; no runtime object/contact truth or assetID actor input',plan=plan,acquisition=json.loads((old/'functional-side-edge-under-support-lateral-v3/acquisition-path.json').read_text()),calibration=json.loads((old/'handover-from-v25-v1.json').read_text()),initial_estimated_plans=records,observation_seed=2026100373,estimate_scope='Per-environment fixed noisy initial observations for developmentpilot, not independent validation or real sensor; original actualcontinuous physicalepisodes preserved')
output=D/'noisy-estimate-scene-v23.json';output.write_text(json.dumps(scene,indent=2));print(json.dumps({'output':str(output.relative_to(R)),'bytes':output.stat().st_size,'observations':len(records)}),flush=True)
from scripts.record_wuji_support_goal import record
record('noisy_initial_observation_motor_schedule_prepared',evidence=str(output.relative_to(R)),config={'observations':len(records),'seed':2026100373,'physical_asset_types':4,'geometry_WT_error_bound_m':.00025,'geometry_L_error_bound_m':.0005,'slider_center_error_bound_m':.00025},conclusion='Common continuous IK with explicit noisy sensor samples, no physicalID/currenttruth actor. Shortpilot before expanding jointtraining.',next='100updates128actualG2 envs withsame load.1-.5/detent.1-.5, finitecommands/history, sensornoise/bias/latency/materials')
