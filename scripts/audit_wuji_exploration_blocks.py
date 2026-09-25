"""Compare every SAPG exploration block on the same nominal initial grasp.

Block identity is an explicit model-selection dimension. This audit does not
replace block0 results or establish generalization to new grasps/perturbations.
"""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
from isaacgymenvs.eval_common import _infer_expl_num_blocks
from isaacgymenvs.student_eval_utils import run_grasp_evaluation_loop
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--trials-per-block',type=int,default=32)
    p.add_argument('--stochastic',action='store_true');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    blocks=_infer_expl_num_blocks(a.checkpoint)
    if not blocks or blocks<2:raise ValueError('Expected a checkpoint with multiple SAPG blocks')
    n=a.trials_per_block;cfg=configuration('wuji_acquisition_precision_aug',blocks*n,
        ['object=knife_wuji_acquisition_precision','test=True'],train='wujiAcquisitionSAPG',seed=2020)
    env,player=make_player(cfg,a.checkpoint)
    ids=torch.linspace(50.,0.,blocks,device=player.device)
    if player.intr_reward_coef_embd is None or player.intr_reward_coef_embd.shape!=(blocks*n,1):
        raise ValueError('Unexpected SAPG coefficient observation layout')
    player.intr_reward_coef_embd[:]=ids.repeat_interleave(n).reshape(-1,1)
    env.configure_grasp_consecutive_evaluation('000',goal_sequence=tuple(cfg.object.task.goals),
        grasp_split='train',episodes_per_grasp=blocks*n)
    if not torch.equal(env.eval_grasp_states,env.eval_grasp_states[:1].expand_as(env.eval_grasp_states)):
        raise ValueError('Nominal block comparison requires a single identical initial state')
    trace=[];reward=env.compute_reward
    def capture(actions):
        active=env.eval_active_mask.clone();reward(actions)
        rotation=2*torch.asin(torch.linalg.vector_norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=1).clamp(0,1))
        trace.append(dict(active=active.cpu().numpy(),events=env.goal_achieved_step.cpu().numpy().copy(),
            rotation=rotation.cpu().numpy(),drift=torch.linalg.vector_norm(env.object_pos-env.init_object_pos,dim=1).cpu().numpy()))
    env.compute_reward=capture
    try:
        stats=run_grasp_evaluation_loop(player,env,deterministic=not a.stochastic,progress_interval_sec=15)
        arrays={k:np.stack([row[k] for row in trace]) for k in trace[0]};np.savez_compressed(a.output/'trace.npz',**arrays)
        records=[]
        for i,cycles in enumerate(stats['consecutive_success_cycles']):
            events=np.flatnonzero(arrays['events'][:,i]*arrays['active'][:,i]);end=events[1]+1 if len(events)>1 else int(arrays['active'][:,i].sum())
            records.append(dict(env=i,block=i//n,cycles=cycles,reason=stats['completion_reason'][i],
                first_cycle_max_drift_m=float(arrays['drift'][:end,i].max()),
                first_cycle_max_rotation_rad=float(arrays['rotation'][:end,i].max())))
        groups=[]
        for b in range(blocks):
            rows=records[b*n:(b+1)*n]
            groups.append(dict(block=b,coefficient_id=float(ids[b]),trials=n,
                success=sum(r['cycles']>=1 for r in rows),
                strict=sum(r['cycles']>=1 and r['first_cycle_max_drift_m']<.01 and r['first_cycle_max_rotation_rad']<.25 for r in rows),
                mean_cycles=float(np.mean([r['cycles'] for r in rows]))))
        report=dict(protocol=__doc__,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
            deterministic=not a.stochastic,seed=2020,groups=groups,records=records)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(groups),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
