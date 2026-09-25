"""Student parity using 50 executed frames, plus a live-truth invariance check."""
import argparse
import json
from pathlib import Path
from isaacgym import gymapi
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.wuji_goal_common import configuration,make_player
from scripts.g2_frozen_policy import FrozenPolicy
from scripts.g2_kinematics import transform
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.eval_common import preprocess_train_config


def main():
    p=argparse.ArgumentParser();p.add_argument('--teacher',type=Path,required=True);p.add_argument('--student',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',1,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=True'],train='wujiAcquisitionSAPG')
    env,player=make_player(cfg,args.teacher)
    s=np.load('caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    env.configure_fixed_grasp_consecutive_evaluation(instance_id='000',grasp_state=s,goal_sequence=(.04,0.),episodes_per_grasp=1)
    env.success_hold_duration=1e9;env.eval_goal_timeout=0;env.set_student_encoder_obs_enabled(True)
    try:
        obs=player.env_reset(player.env);init_player_rnn_for_batch(player,1)
        bridge=FrozenPolicy(cfg,args.teacher,args.student)
        def arr(t):return t.detach().cpu().numpy()
        p=env.hand_start_pose.p;r=env.hand_start_pose.r
        wrist=transform([p.x,p.y,p.z],[r.x,r.y,r.z,r.w])
        obj=wrist@transform(s[40:43],s[43:47]);link=wrist@transform(s[47:50],s[50:54])
        for _ in range(50):
            with torch.no_grad():action=player.get_action(obs,is_deterministic=True)
            obs,_,_,_=player.env_step(player.env,action)
            bridge.record(arr(env.hand_dof_pos)[0],arr(action)[0])
        bridge.takeover(arr(env.hand_dof_pos)[0],s[20:40],wrist,obj,link,float(s[54]),s)
        bridge.last_action=arr(action)[0]
        candidate=bridge.observation(arr(env.hand_dof_pos)[0],wrist,obj,link,float(s[54]),.04)
        override=bridge.player.model.a2c_network.actor_encoder_obs_override.clone()
        expected=env.get_student_encoder_observations()
        student_error=float((override-expected).abs().max())
        actual=obs.clone();actual[:,111:132]=0;actual[:,132:137]=0
        policy_error=float((candidate[:,:111]-actual[:,:111]).abs().max())
        artifact=torch.load(args.student,map_location='cpu')
        encoder,_,_,_=build_student_encoder_from_artifact(player,cfg,
            preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),artifact,artifact['distill_meta'])
        player.model.a2c_network.priv_encoder=encoder;player.model.a2c_network.actor_encoder_obs_override=expected
        init_player_rnn_for_batch(player,1)
        with torch.no_grad():
            a=player.get_action(actual,is_deterministic=True)
            b=bridge.player.get_action(candidate,is_deterministic=True)
        false_obj=obj.copy();false_obj[:3,3]+=[100,-100,50]
        after=bridge.observation(arr(env.hand_dof_pos)[0],wrist,false_obj,false_obj,3.14,.04)
        truth_error=float((after-candidate).abs().max())
        result=dict(actual_history_frames=50,student_input_max_error=student_error,policy_input_max_error=policy_error,
            action_max_error=float((a-b).abs().max()),live_object_truth_invariance_error=truth_error,
            initialized_from='cached hand-base state for this interface parity test, not a table pickup result')
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
        assert student_error<1e-5 and policy_error<1e-4 and float((a-b).abs().max())<1e-3 and truth_error==0
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
