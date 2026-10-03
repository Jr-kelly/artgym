"""Frozen full-scene G2 checks before direct continuous-scene training."""
import argparse,json,hashlib,time
from pathlib import Path
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic
from scripts.wuji_student_interface import tensor_hash
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_robust_learning import R800,TEACHER
import torch,numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--envs',type=int,default=1);p.add_argument('--seed',type=int,default=2026100356)
    p.add_argument('--load-profile',choices=['constant','sinusoidal','triangular','pulse','mixed'],default='sinusoidal');p.add_argument('--load-frequency',type=float,default=1.7);p.add_argument('--load-max',type=float,default=.1);p.add_argument('--detent-max',type=float,default=.1);p.add_argument('--takeover-seconds',type=float,default=16.);p.add_argument('--checkpoint',type=Path);p.add_argument('--nominal',action='store_true')
    p.add_argument('--instances',nargs='+',help='Explicit physical asset instances, repeated across environments; never actor input');p.add_argument('--randomization-scale',type=float,default=0.);p.add_argument('--steps',type=int,default=1080)
    p.add_argument('--compatibility-gate',choices=['strict','deployable','off'],default='strict',help='Preserve original raw154 gate; deployable adds measured/known and final-motor checks; off performs physical development checks only after a separate bridge audit')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
    assert not (a.nominal and a.instances),'Use nominal or explicit physical instance list'
    saved=torch.load(a.checkpoint,map_location='cuda') if a.checkpoint else None
    scene=G2ContinuousScene(a.envs,a.seed,a.randomization_scale,instances=['000'] if a.nominal else a.instances,reference_spec=saved.get('thumb_reference') if saved else None,takeover_seconds=a.takeover_seconds,load_profile=a.load_profile,load_frequency=a.load_frequency,load_max=a.load_max,detent_max=a.detent_max,history_features=saved.get('history_features',False) if saved else False)
    np.savez_compressed(a.output/'initial-snapshot.npz',root=scene.root.cpu().numpy(),dof=scene.dof.cpu().numpy(),materials=scene.material_tensor.cpu().numpy(),observation_bias=scene.observation_bias.cpu().numpy(),delay=scene.delay.cpu().numpy(),cal_object=scene.cal_object.cpu().numpy(),cal_slider=scene.cal_slider.cpu().numpy(),load_amplitude=scene.load_amplitude.cpu().numpy(),detent_amplitude=scene.detent_amplitude.cpu().numpy(),load_phase=scene.load_phase.cpu().numpy(),load_profile_ids=scene.load_profile_ids.cpu().numpy(),load_frequencies=scene.load_frequencies.cpu().numpy())
    model=ResidualActorCritic(scene.public_dim,scene.public_dim+27).to(scene.device)
    if saved:model.load_state_dict(saved['model']);model.eval()
    scale=torch.tensor(saved['action_scale'],device=scene.device) if saved else .25
    frames=[];begin=time.monotonic();base_hash=tensor_hash(scene.player.model.state_dict());parity=None
    try:
        for step in range(a.steps):
            public,critic=scene.features()
            if step==scene.takeover_frame and saved and a.compatibility_gate!='off':
                single=G2R800Policy(scene.cfg,TEACHER,R800,residual_checkpoint=a.checkpoint)
                single.history=[row.copy() for row in scene.bridge.history[0].cpu().numpy()]
                q=scene._measurement[0].cpu().numpy();obj=scene.cal_object[0].cpu().numpy();slider=scene.cal_slider[0].cpu().numpy()
                single.takeover_estimate(q,scene.bridge.known.initial[0].cpu().numpy(),transform(obj[:3],obj[3:]),transform(slider[:3],slider[3:]))
                gravity=G2Kinematics().forward(scene.dof[0,scene.arm_ids,0].cpu().numpy())[:3,:3].T@np.array([0.,0.,-1.])
                expected_target,expected_action=single.command(q,float(scene.goal[0]),wrist_gravity=gravity)
                parity=dict(scope='Same actual measured frames/calibration/issued commands, independent single-G2 and batched bridge; no current truth supplied',actual_history_frames=50,max_encoder_error=float(abs(single.last_encoder_input-scene.bridge.last_encoder_input[0].cpu().numpy()).max()),max_public_error=float(abs(single.last_public_features-public[0].cpu().numpy()).max()),max_raw_base_action_error=float(abs(single.last_raw_action-scene.bridge.base_action[0].cpu().numpy()).max()))
                packet=scene.bridge.last_encoder_input[:1];observation=scene.bridge.last_observation[:1]
                stored_states=scene.player.states
                scene.player.states=[torch.zeros_like(s[:,:1]) for s in stored_states]
                scene.player.model.a2c_network.actor_encoder_obs_override=packet
                with torch.no_grad():same_input_unbatched=scene.player.get_action(observation,is_deterministic=True)
                scene.player.states=stored_states
                single.player.states=[torch.zeros_like(s) for s in single.player.states]
                single.player.model.a2c_network.actor_encoder_obs_override=packet
                with torch.no_grad():same_packet_other_model=single.player.get_action(observation,is_deterministic=True)
                parity.update(model_tensor_hash_equal=tensor_hash(single.player.model.state_dict())==tensor_hash(scene.player.model.state_dict()),same_packet_different_model_error=float((same_packet_other_model-same_input_unbatched).abs().max()),same_model_batch_kernel_error=float((same_input_unbatched[0]-scene.bridge.base_action[0]).abs().max()),same_batch_size_observation_roundoff_error=float(abs(same_input_unbatched[0].cpu().numpy()-single.last_raw_action).max()))
                np.savez_compressed(a.output/'parity-packets.npz',batched_encoder=packet.cpu().numpy(),single_encoder=single.last_encoder_input,batched_observation=observation.cpu().numpy(),single_observation=single.last_observation,batched_action=scene.bridge.base_action[0].cpu().numpy(),same_packet_unbatched_action=same_input_unbatched.cpu().numpy(),single_action=single.last_raw_action)
            with torch.no_grad():residual=model.actor(public) if saved else torch.zeros((a.envs,20),device=scene.device)
            scene.step(residual,scale,reset_failed=False,reset_finished=False)
            if step==scene.takeover_frame and saved and a.compatibility_gate!='off':
                parity['max_motor_target_error_rad']=float(abs(expected_target-scene.target[0,scene.hand_ids].cpu().numpy()).max()) if not bool(scene.delay[0]) else None
                parity['strict_raw154_passed']=max(parity['max_encoder_error'],parity['max_public_error'],parity['max_raw_base_action_error'])<2e-5 and (parity['max_motor_target_error_rad'] is None or parity['max_motor_target_error_rad']<2e-6)
                legal_columns=np.r_[np.arange(131),np.arange(151,154)]
                parity['max_history_latent_error']=float(abs(single.last_public_features[154:]-public[0,154:].cpu().numpy()).max()) if scene.history_features else None
                parity['history_latent_from_same_legal2076_packet']=scene.history_features
                parity['max_measured_known_input_error']=float(abs(single.last_public_features[legal_columns]-public[0].cpu().numpy()[legal_columns]).max())
                parity['deployable_passed']=(not scene.history_features or parity['max_history_latent_error']<2e-5) and parity['model_tensor_hash_equal'] and max(parity['max_encoder_error'],parity['max_measured_known_input_error'],parity['same_packet_different_model_error'],parity['same_batch_size_observation_roundoff_error'])<2e-5 and parity['max_motor_target_error_rad'] is not None and parity['max_motor_target_error_rad']<2e-6
                parity['selected_gate']=a.compatibility_gate
                parity['numerical_scope']='Raw frozen actor means remain reported separately: same packet and model differ with batch kernels. Original strict gate retained, never reclassified. Deployable gate checks measured/known fields, same-packet model semantics and issued motor targets under the supplied residual checkpoint.'
                parity['passed']=parity['strict_raw154_passed'] if a.compatibility_gate=='strict' else parity['deployable_passed']
                (a.output/'bridge-parity.json').write_text(json.dumps(parity,indent=2));print(json.dumps(parity),flush=True);assert parity['passed']
            frames.append({k:v.cpu().numpy().copy() for k,v in scene.last_diagnostics.items()})
            if step%150==0:print(json.dumps(dict(step=step,time_s=(step+1)/30,height=float(frames[-1]['height'].mean()),slider=float(frames[-1]['slider'].mean()))),flush=True)
        assert tensor_hash(scene.player.model.state_dict())==base_hash
        np.savez_compressed(a.output/'trace.npz',**{k:np.stack([f[k] for f in frames]) for k in frames[0]})
        (a.output/'episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in scene.stats))
        report=dict(args=vars(a),physical_asset_instances=scene.instances,physical_asset_parameters=scene.asset_records,completed=sum(r['operation_complete'] for r in scene.stats),n=a.envs,episodes=scene.stats,bridge_parity=parity,wall_seconds=time.monotonic()-begin,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest() if a.checkpoint else None,scope='Actual parallel G2 continuous scene check; proximity/net-contact proxy, no exact pair force; no stage resets or object-state assistance',physics='GPU state pipeline; same240Hz finite clipped PD/gravity motors,30Hz legal policy/action memory, original G2+Wuji/knife gravity and collisions',actor=f'2076 frozenR800 history encoder,{scene.public_dim} legal measured/known features; unchanged nominal geometry and once-loaded prior calibration')
        (a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps({k:report[k] for k in ['completed','n','wall_seconds','scope']}))
    finally:scene.close()


if __name__=='__main__':main()
