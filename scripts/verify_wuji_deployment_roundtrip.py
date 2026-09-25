"""Compare CPU deployment observations/actions with the simulator, no hardware.

The simulator supplies encoders and reset-only geometry to the deployment path.
Goal commands are supplied by the same task sequencer. This verifies numerical
parity, not real sensor calibration, socket latency or hardware success.
"""
import argparse,hashlib,json
from pathlib import Path
from types import SimpleNamespace

from scripts.wuji_goal_common import configuration,make_player
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.deploy._client_impl import build_local_task_env,RemoteStudentPolicyDeployer,reset_deployer_from_robot
from isaacgymenvs.deploy.real_robot_policy_api import TaskResetState
from isaacgymenvs.deploy.wuji.observation_provider import WujiTaskObservationProvider
from isaacgymenvs.deploy.student_policy_runtime import load_student_policy_runtime
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.eval_common import preprocess_train_config
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch


def numpy0(t):return t[0].detach().cpu().numpy().copy()


class InitialStateProvider:
    def __init__(self,env):self.env=env
    def reset(self,robot):pass
    def before_reset_capture(self,robot):pass
    def before_rollout_start(self,robot,state):pass
    def get_goal_offset(self,robot,state):
        return float((self.env.goal_obj_dof_pos-self.env.init_obj_dof_pos)[0,0])
    def build_reset_state(self,robot,q,tips):
        e=self.env
        return TaskResetState(init_object_pos=numpy0(e.init_object_pos),init_object_rot=numpy0(e.init_object_rot),
            goal_offset=self.get_goal_offset(robot,None),init_hand_qpos=numpy0(e.init_hand_dof_pos),
            init_fingertip_pos=numpy0(e.init_fingertip_pos),metadata=dict(pose_frame='hand_base',
                init_link1_pose=numpy0(e.init_link1_pose),link0_bbx=numpy0(e.init_link0_bbx),
                link1_bbx=numpy0(e.init_link1_bbx),commanded_initial_targets=numpy0(e.init_targets)[:20]))


def main():
    p=argparse.ArgumentParser();p.add_argument('--teacher',type=Path,required=True)
    p.add_argument('--student',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--task',default='wuji_acquisition_precision')
    p.add_argument('--hand',default='wuji_paper')
    p.add_argument('--object',default='knife_wuji_acquisition_precision')
    p.add_argument('--steps',type=int,default=400);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cfg=configuration(a.task,1,['object='+a.object,'hand='+a.hand,'test=True'],
        train='wujiAcquisitionSAPG',seed=1111)
    env,player=make_player(cfg,a.teacher)
    artifact=torch.load(a.student,map_location='cpu')
    encoder,_,_,_=build_student_encoder_from_artifact(player,cfg,
        preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),artifact,artifact['distill_meta'])
    player.model.a2c_network.priv_encoder=encoder;player.model.eval();env.set_student_encoder_obs_enabled(True)
    runtime=load_student_policy_runtime(str(a.student),str(a.teacher),a.task,
        'wujiAcquisitionSAPG',a.hand,a.object,'',str(player.device),1111,0)
    remote=runtime.init_session('parity')
    local=build_local_task_env(a.task,a.hand,a.object)
    deployer=RemoteStudentPolicyDeployer(local,remote,'parity',True)
    provider=WujiTaskObservationProvider();provider.set_deployment_context(deployer.build_context())
    provider.set_task_state_provider(InitialStateProvider(env))
    robot=SimpleNamespace(get_hand_joint_positions=lambda:numpy0(env.hand_dof_pos))
    obs=player.env_reset(player.env);provider.reset(robot);reset_deployer_from_robot(deployer,robot,provider)
    previous=np.zeros(20,dtype=np.float32);errors=[];resets=0
    try:
        for step in range(a.steps):
            cpu=provider.build_observations(robot,previous)
            expected_policy=numpy0(env.obs_buf)[:111];expected_student=numpy0(env.get_student_encoder_observations())
            player.model.a2c_network.actor_encoder_obs_override=env.get_student_encoder_observations()
            with torch.no_grad():reference=player.get_action(obs,is_deterministic=True)
            response=runtime.infer('parity',cpu.policy_obs,cpu.student_obs,deterministic=True,reset_rnn=deployer.need_reset_rnn)
            actual=np.asarray(response['action'],dtype=np.float32)
            target=deployer._action_to_joint_targets(actual);deployer.need_reset_rnn=False
            expected_target=numpy0(env.actions_to_targets(reference))
            errors.append(dict(policy_obs=float(np.max(np.abs(cpu.policy_obs-expected_policy))),
                student_obs=float(np.max(np.abs(cpu.student_obs-expected_student))),
                action=float(np.max(np.abs(actual-numpy0(reference)))),
                joint_target=float(np.max(np.abs(target-expected_target)))))
            obs,_,done,_=player.env_step(player.env,reference)
            previous=numpy0(reference)
            if bool(done[0]):
                init_player_rnn_for_batch(player,1);provider.reset(robot)
                reset_deployer_from_robot(deployer,robot,provider);previous.fill(0);resets+=1
        maxima={k:max(row[k] for row in errors) for k in errors[0]}
        passed=maxima['policy_obs']<2e-5 and maxima['student_obs']<2e-6 and maxima['action']<2e-4 and maxima['joint_target']<2e-4
        report=dict(status='passed' if passed else 'failed',steps=a.steps,resets=resets,max_abs_errors=maxima,
            task=a.task,hand=a.hand,object=a.object,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            teacher_sha256=hashlib.sha256(a.teacher.read_bytes()).hexdigest(),student_sha256=hashlib.sha256(a.student.read_bytes()).hexdigest(),
            action_control=remote['action_control'],scope=__doc__,errors=errors)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='errors'}),flush=True)
        if not passed:raise RuntimeError('Deployment parity failed; see per-step errors')
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
