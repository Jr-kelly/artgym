"""Actual simulation checks for new objective timing, reset and static body validity."""
import json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
import torch
from omegaconf import OmegaConf
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate

def main():
    out=Path('runs/artmanip-recovery-20260930/holding-precheck');out.mkdir(parents=True,exist_ok=False)
    cfg=configuration('wuji_artmanip_clock_hold',128,['object=knife_wuji_reference','hand=wuji_paper_official_actuator'],train='wujiArtManipReferenceSAPG',seed=2026093091)
    (out/'resolved.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env=make_env(cfg);env.reset_idx(torch.arange(env.num_envs,device=env.device));env.compute_observations();env.reset()
    periods=env.clock_period.clone();source=env.source_ids.clone();initial=env.init_targets[:,:20].clone();object_target=env.prev_targets[:,20:].clone()
    counts={};max_map=0.;stable_all=torch.ones(128,dtype=torch.bool,device=env.device);rows=[]
    try:
        for step in range(600):
            obs,reward,done,info=env.step(torch.zeros((128,20),device=env.device))
            assert torch.isfinite(reward).all() and torch.isfinite(env.hand_dof_pos).all()
            assert not done.any() if step<599 else done.all()
            if step<599:assert torch.equal(env.prev_targets[:,20:],object_target)
            if step<599:max_map=max(max_map,float((env.cur_targets[:,:20]-initial).abs().max()))
            stable=(torch.linalg.vector_norm(env.object_pos-env.init_object_pos,dim=-1)<.01)
            angle=2*torch.asin(torch.linalg.vector_norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
            stable_all &= stable & (angle<.25)
            assert float(info['holding/max_abs_additional_reward'])<=25.00001
            expected_switch=((step+1)%periods==0)&(step<599)
            assert int(info['holding/switches_this_step'])==int(expected_switch.sum())
            if expected_switch.any():rows.append(dict(step=step+1,count=int(expected_switch.sum())))
            if step==598:assert torch.equal(env.clock_switches,torch.where(periods==60,9,3))
        assert max_map<1e-6 and stable_all.all()
        assert set(periods.cpu().tolist())=={60,150}
        assert (env.clock_switches==0).all(),'600-step reset did not clear clock'
        for s in range(4):counts[str(s)]=int((source==s).sum())
        before_visits=env.source_visits.clone();env.reset_idx(torch.arange(128,device=env.device))
        assert (env.progress_buf==0).all() and (env.clock_switches==0).all()
        assert torch.allclose(env.goal_obj_dof_pos[:,0],env.init_obj_dof_pos[:,0]+.04)
        assert int((env.source_visits-before_visits).sum())==128
        result=dict(passed=True,scope='20second zero-action static and training-objective scheduling precheck; not learned manipulation',steps=600,initial_source_counts=counts,period2_count=int((periods==60).sum()),period5_count=int((periods==150).sum()),switch_events=rows,map_max_error=max_map,body_position_all128=True,object_targets_unchanged=True,reset_clock_verified=True,training_states_sha256=env.training_states_sha256,task_source_sha256=hashlib.sha256(Path('isaacgymenvs/tasks/wuji_artmanip_clock_hold.py').read_bytes()).hexdigest())
        (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:env.gym.destroy_sim(env.sim)

if __name__=='__main__':main()
