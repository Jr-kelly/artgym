"""New staged-prefix and per-episode bank contract, not a demo evaluation."""
import json,pathlib,copy,time
from scripts.g2_continuous_scene import G2ContinuousScene,smooth
from scripts.wuji_robust_learning import ResidualActorCritic
def record(*a,**k):pass
import torch,numpy as np

R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/support-pressure-20261003';B=R/'runs/support-pressure-20261003'
scene=json.loads((D/'staged-support-estimate-scene256-v88.json').read_text())
selected=[0,2,64,66];scene['initial_estimated_plans']=[scene['initial_estimated_plans'][i] for i in selected]
instances=['s0000','s0002','s0000','s0002'];registry=json.loads((D/'joint-training-registry-v26.json').read_text())
assets={r['instance']:r['directory'] for r in registry['entries']};out=B/'preparation-bridge-contract-v117';out.mkdir(exist_ok=False)
record('staged_prefix_bridge_v90_started',evidence=str(out.relative_to(R)),config={'envs':4,'prefixes':8,'physical_types':2,'initial_observations':4},next='Check newmotorpaths inactualG2 and atnewepisode resampling, not fulloutcome/parityreaudit')
system=G2ContinuousScene(4,2026100420,0.,instances=instances,load_max=.5,detent_max=.5,
    reference_spec=json.loads((D/'coordinated-thumb-reference-v11.json').read_text()),
    support_scale=.025,thumb_scale=.12,takeover_seconds=14.3,load_profile='pulse',load_frequency=2.9,
    scene_spec=scene,asset_registry=assets,resample_initial_estimates=True,
    action_parameterization='bounded-motor-offset',resistance_integration='solver-brake',load_min=.5,detent_min=.5)
saved=torch.load(B/'train/joint-noisier-continuation-v31/update_000750.pth',map_location=system.device)
model=ResidualActorCritic().to(system.device);model.load_state_dict(saved['model']);model.eval()
begin=time.monotonic();results=[]
try:
    for episode in range(1):
        if episode:system.reset(torch.arange(4,device=system.device))
        choices=system.initial_observation_indices.cpu().tolist();maximum_error=0.;constant_error=0.
        for step in range(510):
            public,critic=system.features()
            if 360<=step<429:
                _,actual=system.prefix_targets();t=step/30
                expected=[]
                for index in choices:
                    rows=scene['initial_estimated_plans'][index]['support_motor_waypoints']
                    desired=np.asarray(rows[-1]['q'])
                    for first,last in zip(rows[:-1],rows[1:]):
                        if t<=last['time_s']:
                            u=np.clip((t-first['time_s'])/(last['time_s']-first['time_s']),0,1);u=u**3*(10-15*u+6*u*u)
                            desired=np.asarray(first['q'])*(1-u)+np.asarray(last['q'])*u;break
                    expected.append(desired)
                error=float(np.abs(actual.cpu().numpy()-expected).max());maximum_error=max(maximum_error,error)
                if step>=426:constant_error=max(constant_error,float(np.abs(actual.cpu().numpy()-system.support_waypoint_q[:,-1].cpu().numpy()).max()))
            with torch.no_grad():residual=model.actor_logits(public)
            if step==480:latched=residual[:,:16].clone()
            if step>=480:residual[:,:16]=latched
            system.step(residual,reset_failed=False,reset_finished=False)
            if step==480:latched_targets=system.command_target[:,system.hand_ids][:,:16].clone()
            if step>480:assert (system.command_target[:,system.hand_ids][:,:16]-latched_targets).abs().max()<2e-7
        assert maximum_error<2e-6 and constant_error<1e-7
        assert bool((system.bridge.history_count>=50).all())
        assert bool((system.support_waypoint_q==system.estimate_bank['support_waypoint_q'][system.initial_observation_indices]).all())
        results.append(dict(episode=episode,selected_observations=choices,maximum_native_formula_target_error_rad=maximum_error,final_stage_motor_target_error_rad=constant_error,actual_history_counts=system.bridge.history_count.cpu().tolist()))
    report=dict(scope='Four actualG2 earlypreparation prefixes, completedstage before429; actualcontinuoushistory and 29heldsupportcommands verified after480; incompleteoperation not counted as fullcontinuousdemo or independentvalidation.',passed=True,results=results,wall_seconds=time.monotonic()-begin)
    (out/'report.json').write_text(json.dumps(report,indent=2));record('staged_prefix_bridge_v90_passed',evidence=str(out.relative_to(R)/'report.json'),config=report,next='Launch shortmatched learning on full256observation/64physicalfamily');print(json.dumps(report))
finally:system.close()
