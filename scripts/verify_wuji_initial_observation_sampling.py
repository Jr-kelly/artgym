"""One physical contract check of episode-only initial-observation resampling.

Four actual G2 TABLE environments use four noisy observations of one training
geometry. This checks observation/plan/history coupling across real episode
boundaries, not policy generalization, force calibration or bitwise recovery.
"""
import argparse,hashlib,json,pathlib,time
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic
from scripts.record_wuji_support_goal import record
import torch

R=pathlib.Path(__file__).resolve().parents[1];D=R/'research/support-pressure-20261003'


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    scene=json.loads((D/'joint-looser-estimate-scene256-v32.json').read_text())
    samples=[0,64,128,192];bank=[scene['initial_estimated_plans'][i] for i in samples]
    scene['initial_estimated_plans']=bank
    checkpoint=R/'runs/support-pressure-20261003/train/estimated-offset-takeover16-v23/update_000100.pth'
    identity=dict(weight_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),bank_source_indices=samples,
                  scope=__doc__,source_sha256=hashlib.sha256((R/'scripts/g2_continuous_scene.py').read_bytes()).hexdigest())
    (a.output/'identity.json').write_text(json.dumps(identity,indent=2))
    record('initial_observation_sampling_physical_contract_started',evidence=str(a.output/'identity.json'),config=identity,
           next='Actualcontinuous episodes with bank-index/initialestimateddimensions/issuedtargets checks; no stage resets')
    registry={row['instance']:row['directory'] for row in json.loads((D/'joint-training-registry-v26.json').read_text())['entries']}
    system=None;start=time.monotonic();snapshots=[]
    try:
        system=G2ContinuousScene(4,2026100389,1.,instances=['s0000']*4,load_min=.1,load_max=.5,
            detent_min=.1,detent_max=.5,load_profile='mixed',support_scale=.025,thumb_scale=.12,
            functional_thumb_reward=True,scene_spec=scene,asset_registry=registry,
            resistance_integration='solver-brake',action_parameterization='bounded-motor-offset',resample_initial_estimates=True)
        model=ResidualActorCritic(154,181).to(system.device);model.load_state_dict(torch.load(checkpoint,map_location='cpu')['model']);model.eval()
        observed=set();checks=0
        for frame in range(2160):
            fresh=(system.age==0).nonzero(as_tuple=False).flatten()
            for i in fresh.tolist():
                index=int(system.initial_observation_indices[i]);observed.add(index);row=bank[index]
                size=system.bridge.geometry[i,:3].cpu()
                expected=torch.tensor(row['estimate']['handle_size_WTL_m'])
                assert torch.allclose(size,expected,rtol=0,atol=1e-8)
                assert torch.allclose(system.bridge.init[i,49:52].cpu(),expected,rtol=0,atol=1e-8)
                desired=torch.tensor(row['motor_plan']['open_q'],device=system.device)
                assert torch.allclose(system.command_target[i,system.hand_ids],desired,rtol=0,atol=1e-7)
                assert int(system.bridge.history_count[i])==0
                checks+=1;snapshots.append(dict(global_frame=frame,env=i,sample=index,estimated_size_WTL_m=size.tolist()))
            with torch.no_grad():residual=model.actor(system.features()[0])
            system.step(residual)
        assert checks>4 and len(observed)>1,'No actual observation variation across episode resets'
        result=dict(passed=True,checked_new_episode_starts=checks,observed_bank_indices=sorted(observed),
                    snapshots=snapshots,actual_training_episodes=system.stats,wall_seconds=time.monotonic()-start,
                    scope='Physical observation/plan/history coupling check only; net-contact training proxy, not native pair force or frozen generalization')
        (a.output/'result.json').write_text(json.dumps(result,indent=2))
        record('initial_observation_sampling_physical_contract_closed',evidence=str(a.output/'result.json'),
               conclusion=f'{checks} actualnew-episode starts checked; estimatedgeometry, motorplan andhistory initialized consistently, {len(observed)} distinctnoisyobservations seen. No stage statewrites.',
               next='Use this episode sampler in necessary jointtraining; preserve separate native/frozen validation')
    except Exception as error:
        record('initial_observation_sampling_physical_contract_failed',evidence=str(a.output),conclusion=repr(error),
               next='Correctactualsampling/initialization failure before any further training extension')
        raise
    finally:
        if system is not None:system.close()


if __name__=='__main__':main()
