"""Actual control mapping and static reset validation; no policy skill claim."""
import json,argparse,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
import torch,numpy as np
from omegaconf import OmegaConf
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    cfg=configuration('wuji_artmanip_reference',128,['hand=wuji_paper_official_actuator','object=knife_wuji_reference'],train='wujiArtManipReferenceSAPG',seed=2026093010)
    env=make_env(cfg);env.reset()
    (a.output/'resolved.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    ids=torch.arange(128,device=env.device);env.reset_idx(ids)
    previous=env.prev_targets.clone();action=torch.ones((128,20),device=env.device)*.5
    expected=torch.maximum(torch.minimum(previous[:,:20]+.5*env.dt*env.hand_dof_speed_scale,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
    env.pre_physics_step(action)
    mapping_error=float((env.cur_targets[:,:20]-expected).abs().max())
    object_target_error=float((env.cur_targets[:,20:]-previous[:,20:]).abs().max())
    env.reset_idx(ids);sources=env.source_ids.clone();q0=env.init_hand_dof_pos.clone();target0=env.init_targets.clone();data=[]
    original=env.compute_reward
    def observe(actions):
        original(actions)
        angle=2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
        data.append(dict(drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1).cpu().numpy(),rotation=angle.cpu().numpy(),done=env.reset_buf.cpu().numpy().copy(),q=env.hand_dof_pos.cpu().numpy().copy()))
    env.compute_reward=observe
    for _ in range(30):env.step(env.zero_actions())
    trace={k:np.stack([r[k] for r in data]) for k in data[0]};np.savez_compressed(a.output/'trace.npz',source=sources.cpu().numpy(),**trace)
    rows=[]
    for source in range(4):
        mask=sources.cpu().numpy()==source;valid=(~trace['done'].astype(bool)).all(0);body=(trace['drift']<.01).all(0)&(trace['rotation']<.25).all(0)&valid
        rows.append(dict(source=source,n=int(mask.sum()),alive=int(valid[mask].sum()),body=int(body[mask].sum()),max_drift=float(trace['drift'][:,mask].max()),max_rotation=float(trace['rotation'][:,mask].max())))
    result=dict(mapping_error=mapping_error,object_target_change=object_target_error,effective_step=float(env.dt*env.hand_dof_speed_scale),control_dt=float(env.dt*env.control_freq_inv),policy_calls=30,physics_steps=120,rows=rows,source_visits=env.source_visits.cpu().tolist(),joint_names=env.gym.get_asset_dof_names(env.hand_asset),joint_limits=[env.hand_dof_lower_limits.cpu().tolist(),env.hand_dof_upper_limits.cpu().tolist()],reward_weights=env.reward_scales_current,passed=mapping_error<1e-6 and object_target_error==0 and all(x['alive']==x['n'] and x['body']/x['n']>=.95 for x in rows))
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));env.gym.destroy_sim(env.sim)
    assert result['passed']
if __name__=='__main__':main()
