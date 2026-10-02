"""Compare legal G2 bridge with the working simulator interface after actual history.
Calibration is ideal simulation data for this compatibility check only.
"""
from scripts.wuji_robust_learning import LearningSystem,ResidualActorCritic,TEACHER,R800,R
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import transform
from scripts.wuji_student_interface import legal_policy_observation
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
from isaacgymenvs.utils.torch_jit_utils import quat_mul
from scipy.spatial.transform import Rotation
import argparse,json,hashlib,numpy as np,torch
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    system=LearningSystem(12,randomization_scale=0,loadmax=0,detentmax=0,delay=0)
    try:
        # All histories below come from sixty actual control transitions.
        for _ in range(60):system.features();system.step(torch.zeros((12,20),device=system.env.device))
        env=system.env;bridge=G2R800Policy(system.cfg,TEACHER,R800,geometry=env.instance_link0_bbx[0].tolist()+env.instance_link1_bbx[0].tolist(),residual_checkpoint=a.checkpoint)
        pol=system.obs[:1,:111].clone();initial=pol[:,:55].clone()
        rotation=torch.tensor([.7071067811865476,0.,0.,.7071067811865476],device=env.device)[None]
        for st in [23,30]:initial[:,st:st+4]=quat_mul(initial[:,st:st+4],rotation)
        for st in [49,52]:initial[:,st:st+3]=initial[:,[st,st+2,st+1]]
        raw=initial[0].cpu().numpy();lower=bridge.fk.lower;upper=bridge.fk.upper
        q0=(raw[:20]+1)*.5*(upper-lower)+lower
        history=env.student_obs_buf[0,:2000].reshape(50,40).cpu().numpy()
        bridge.history=[x.copy() for x in history]
        bridge.takeover_estimate(q0,env.known_controller.initial[0].cpu().numpy(),transform(raw[20:23],raw[23:27]),transform(raw[27:30],raw[30:34]))
        bridge.known.issued[:]=env.known_controller.issued[:1]
        bridge.last_action=env.actions[0].cpu().numpy().copy()
        q=(pol[0,55:75].cpu().numpy()+1)*.5*(upper-lower)+lower;goal=float(pol[0,95])
        obs,x=bridge.inputs(q,goal)
        expected_obs=legal_policy_observation(system.obs[:1]);expected_x=env.student_obs_buf[:1]
        inputerror=float((x-expected_x).abs().max());obserror=float((legal_policy_observation(obs)-expected_obs).abs().max())
        incoming=[v[:,:1].clone() for v in system.player.states]
        bridge.player.states=[v.clone() for v in incoming]
        net=system.player.model.a2c_network;net.actor_encoder_obs_override=expected_x
        # player has n=12; compare batch row0 without altering physics, preserving incoming RNN.
        oldstates=system.player.states;system.player.states=[v.clone() for v in incoming]
        with torch.no_grad():action=system.player.get_action(expected_obs,is_deterministic=True)
        system.player.states=oldstates
        publicerror=0.
        gravity=env.gravity_vector[:1]
        if a.checkpoint:
            saved=torch.load(a.checkpoint,map_location=env.device);model=ResidualActorCritic().to(env.device);model.load_state_dict(saved['model']);model.eval()
            public=torch.cat([expected_obs[:,:111],env.known_controller.observed_targets()[:1],action,gravity],-1)
            base=action if saved.get("action_base_mode","r800")=="r800" else torch.zeros_like(action)
            if saved.get('action_base_mode')=='geometric':
                from scripts.wuji_scheduled_thumb_reference import ScheduledThumbReference
                reference=ScheduledThumbReference(saved['thumb_reference'],1,env.device)
                base=reference.action(env.known_controller.initial[:1],env.known_controller.issued[:1],public[:,95])
            with torch.no_grad():action=(base+torch.tensor(saved['action_scale'],device=env.device)*torch.tanh(model.actor(public))).clamp(-1,1)
        target,bridged_action=bridge.command(q,goal,wrist_gravity=gravity[0].cpu().numpy())
        if a.checkpoint:publicerror=float(np.max(np.abs(bridge.last_public_features-public.cpu().numpy()[0])))
        known=env.known_controller;previous=known.issued.clone();init=known.initial.clone()
        from scripts.wuji_known_controller import KnownWujiController
        other=KnownWujiController(known.lower,known.upper,1);other.initial[:]=init[:1];other.issued[:]=previous[:1]
        motor=other.step(action)[0].cpu().numpy();actionerror=float(np.max(np.abs(bridged_action-action[0].cpu().numpy())));targeterror=float(np.max(np.abs(target-motor)))
        row=dict(actual_history_frames=50,physics_control_steps=60,encoder_dimensions=2076,max_encoder_input_error=inputerror,max_legal_observation_error=obserror,max_public_features_error=publicerror,max_action_error=actionerror,max_motor_target_error_rad=targeterror,residual_checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest() if a.checkpoint else None,calibration_scope='Ideal one-time simulation calibration for interface check only; no real perception evidence',current_inputs='Measured q/FK/history,issued targets,scheduled task goal and wrist gravity from arm FK',passed=max(inputerror,obserror,publicerror)<2e-5 and actionerror<2e-5 and targeterror<2e-6)
        np.savez_compressed(a.output/'comparison.npz',bridge_input=x.cpu().numpy(),reference_input=expected_x.cpu().numpy(),bridge_observation=obs.cpu().numpy(),reference_observation=expected_obs.cpu().numpy(),bridge_motor_target=target,reference_motor_target=motor)
        (a.output/'report.json').write_text(json.dumps(row,indent=2));print(json.dumps(row));assert row['passed']
    finally:system.close()
if __name__=='__main__':main()
