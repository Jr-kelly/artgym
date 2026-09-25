"""Compare the extracted observation bridge to the unchanged ArtGym environment."""
import argparse
import json
from pathlib import Path
from isaacgym import gymapi
import numpy as np
import torch
from scripts.wuji_goal_common import configuration,make_player
from scripts.g2_frozen_policy import FrozenPolicy
from scripts.g2_kinematics import transform
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',1,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=True'],train='wujiAcquisitionSAPG')
    env,player=make_player(cfg,args.checkpoint)
    s=np.load('caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    env.configure_fixed_grasp_consecutive_evaluation(instance_id='000',grasp_state=s,goal_sequence=(.04,0.),episodes_per_grasp=1)
    try:
        obs=player.env_reset(player.env);init_player_rnn_for_batch(player,1)
        bridge=FrozenPolicy(cfg,args.checkpoint)
        def arr(t):return t.detach().cpu().numpy()
        p=env.hand_start_pose.p;r=env.hand_start_pose.r
        w=np.array([p.x,p.y,p.z,r.x,r.y,r.z,r.w])
        wrist=transform(w[:3],w[3:]);obj=wrist@transform(s[40:43],s[43:47]);link=wrist@transform(s[47:50],s[50:54])
        bridge.takeover(arr(env.hand_dof_pos)[0],s[20:40],wrist,obj,link,float(s[54]),s)
        candidate=bridge.observation(arr(env.hand_dof_pos)[0],wrist,obj,link,float(s[54]),.04).cpu()
        actual=obs.cpu() if torch.is_tensor(obs) else obs['obs'].cpu()
        delta=(candidate-actual).abs()[0]
        rows=[dict(index=int(i),candidate=float(candidate[0,i]),reference=float(actual[0,i]),error=float(delta[i])) for i in torch.where(delta>1e-5)[0]]
        with torch.no_grad():
            a=player.get_action(obs,is_deterministic=True).cpu().numpy()
            b=bridge.player.get_action(candidate.to(bridge.player.device),is_deterministic=True).cpu().numpy()
        result=dict(max_observation_error=float(delta.max()),different_features=rows,max_action_error=float(np.abs(a-b).max()),
                    teacher_expected=a.tolist(),teacher_candidate=b.tolist(),
                    student_init_contract='Original task uses RAW _get_init_obs; the actor uses the converted convention. These must remain separate.')
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
