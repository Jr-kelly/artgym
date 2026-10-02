"""Frozen development/confirmation manipulation checks; continuous physics, no reset.
Starts in proxy held grasps, not tabletop pickup. Fifty actual hold frames precede
external extend/hold/retract/hold commands. Every initial attempt stays counted.
"""
import argparse,json,hashlib,time
from pathlib import Path
from scripts.wuji_robust_learning import LearningSystem,ResidualActorCritic,R800,TEACHER
from isaacgymenvs.distill import reset_done_rnn_states
import torch,numpy as np
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path);p.add_argument('--envs',type=int,default=96);p.add_argument('--seed',type=int,default=2026100311);p.add_argument('--load-max',type=float,default=.1);p.add_argument('--detent-max',type=float,default=.1);p.add_argument('--randomization-scale',type=float,default=.5);p.add_argument('--heldout',action='store_true');p.add_argument('--wrist-nominal',type=Path);p.add_argument('--wrist-probability',type=float,default=.5);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    instances=['012','013','014','015'] if a.heldout else None
    wrist=json.loads(a.wrist_nominal.read_text())['wrist_quaternion_xyzw'] if a.wrist_nominal else None
    system=LearningSystem(a.envs,a.seed,a.randomization_scale,a.load_max,a.detent_max,instances=instances,wrist_nominal=wrist,wrist_probability=a.wrist_probability,history_hold_frames=0);env=system.env;model=ResidualActorCritic().to(env.device)
    if a.checkpoint:
        saved=torch.load(a.checkpoint,map_location=env.device);model.load_state_dict(saved['model']);model.eval()
        system.scale=torch.tensor(saved['action_scale'],device=env.device)
    # Fresh test pools replace train sampling once, before this diagnostic episode.
    for instance_index in range(len(env.instance_id_list)):
        env._ensure_grasp_split_loaded(instance_index,'test')
    env._refresh_grasp_split_tensors()
    env.runtime_grasp_split='test';system.obs=system.player.env_reset(system.player.env)
    frames=[];original_reward=env.compute_reward
    def capture(action):
        goal=env.goal_obj_dof_pos[:,0].clone();original_reward(action)
        angle=2*torch.asin(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3].norm(dim=1).clamp(0,1))
        frames.append({k:v.detach().cpu().numpy().copy() for k,v in dict(goal=goal-env.init_obj_dof_pos[:,0],slider=env.obj_dof_pos[:,0]-env.init_obj_dof_pos[:,0],drift=(env.object_pos-env.init_object_pos).norm(dim=1),rotation=angle,fall=env.debug_reset_cause_fall,invalid=env.debug_reset_cause_invalid,contact=env.contact_info,q=env.hand_dof_pos,target=env.cur_targets[:,:20],action=env.actions,force=env.load_force,init_object=env.init_object_pos,object=env.object_pose).items()})
    env.compute_reward=capture
    # Single evaluation episode: failure and timeout must not reset physics state.
    env.reset_idx=lambda *args,**kwargs:None
    try:
        zero=torch.zeros((a.envs,20),device=env.device)
        env.goal_obj_dof_pos[:]=env.init_obj_dof_pos;env.command_deadline[:]=1000000
        for _ in range(50):system.obs,_,_,_=system.player.env_step(system.player.env,zero)
        hold_end=len(frames);hold_bad=np.stack([f['fall']|f['invalid'] for f in frames]).any(0)
        frames.clear();env.progress_buf.zero_();env.command_deadline[:]=1000000
        # Preserve the parallel actor batch; deploy reset helper intentionally assumes one robot.
        system.player.init_rnn()
        reset_done_rnn_states(system.player,torch.ones(a.envs,dtype=torch.bool,device=env.device))
        system._features=None
        begin=time.monotonic()
        for step in range(600):
            env.goal_obj_dof_pos[:]=env.init_obj_dof_pos+(.04 if (step//150)%2==0 else 0.)
            # Refresh only the known task command; actual history is retained.
            system.obs[:,95]=.04 if (step//150)%2==0 else 0.
            env.student_obs_buf[:,-1]=system.obs[:,95]/.04
            public,critic=system.features()
            with torch.no_grad():residual=model.actor(public) if a.checkpoint else torch.zeros_like(zero)
            system.step(residual)
        trace={k:np.stack([f[k] for f in frames]) for k in frames[0]};np.savez_compressed(a.output/'trace.npz',**trace)
        rows=[]
        for i in range(a.envs):
            fall=bool(trace['fall'][:,i].any() or trace['invalid'][:,i].any());stable=bool((trace['drift'][:,i]<.01).all() and (trace['rotation'][:,i]<.25).all())
            endpoints=[float(trace['slider'][max(0,(s+1)*150-9):(s+1)*150,i].mean()) for s in range(4)]
            extend=all(x>.025 for x in [endpoints[0],endpoints[2]]);retract=all(x<.008 for x in [endpoints[1],endpoints[3]])
            rows.append(dict(env=i,instance=env.instance_id_list[i%len(env.instance_id_list)],initial_hold_valid=not bool(hold_bad[i]),fall=fall,body_stable=stable,meaningful_extend=extend,meaningful_retract=retract,operation_complete=not bool(hold_bad[i]) and not fall and stable and extend and retract,endpoints_m=endpoints,peak_extension_m=float(trace['slider'][:,i].max()),contact_fraction=float(trace['contact'][:,i,0].mean()),failure='initial hold' if hold_bad[i] else 'body unstable/drop' if fall or not stable else 'extension' if not extend else 'retraction' if not retract else None))
        report=dict(model=str(a.checkpoint) if a.checkpoint else 'frozenR800',checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest() if a.checkpoint else hashlib.sha256(R800.read_bytes()).hexdigest(),args=vars(a),n=a.envs,completed=sum(r['operation_complete'] for r in rows),initial_hold_valid=sum(r['initial_hold_valid'] for r in rows),stable=sum(r['body_stable'] and not r['fall'] for r in rows),extend=sum(r['meaningful_extend'] for r in rows),retract=sum(r['meaningful_retract'] for r in rows),records=rows,actual_hold_history_frames=50,wall_seconds=time.monotonic()-begin,predeclared='Four5s stages,unchanged40mm command;meanfinal0.3s extension>25mm/retraction<8mm,wholebody<10mm/.25rad,no fall. Presetheld manipulation only.',scope='Frozen development manipulation diagnostic' if not a.heldout else 'Independent held-out geometry manipulation check; no tabletop acquisition')
        (a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps({k:report[k] for k in ['model','n','completed','initial_hold_valid','stable','extend','retract','scope']}))
    finally:system.close()
if __name__=='__main__':main()
