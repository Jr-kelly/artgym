"""Student-only physics, absolute/incremental command supervision from frozen teacher.

Half each optimizer batch is fixed teacher data; half is a FIFO of this
student's own physical states. The teacher supplies labels, never controls the
hand. This is a Wuji transfer experiment, not the paper's latent-MSE student.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
import numpy as np
import torch
from torch.nn import functional as F
from scripts.wuji_absolute_target_student import TargetStudent,features,action_from_prediction,SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import atomic_json,now
from isaacgymenvs.distill import reset_done_rnn_states

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--updates',type=int,default=500)
    p.add_argument('--num-envs',type=int,default=1024);p.add_argument('--lr',type=float,default=2e-5)
    p.add_argument('--seed',type=int,default=20261080);p.add_argument('--runtime-check',action='store_true')
    p.add_argument('--replay-capacity',type=int,default=262144)
    p.add_argument('--restore-optimizer',action='store_true')
    p.add_argument('--thumb-loss-scale',type=float,default=1.)
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    artifact=torch.load(args.artifact,map_location='cpu');arm=artifact['arm']
    assert args.thumb_loss_scale>0 and (arm=='incremental' or args.thumb_loss_scale==1.)
    artifact_sha=hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    assert artifact_sha==json.loads(args.artifact.with_suffix('.json').read_text())['sha256']
    assert hashlib.sha256(args.data.read_bytes()).hexdigest()==artifact['provenance']['dataset_sha256']
    teacher=ROOT/TEACHER;teacher_sha=hashlib.sha256(teacher.read_bytes()).hexdigest()
    assert teacher_sha==artifact['provenance']['teacher_sha256']
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',args.num_envs,
        ['object=knife_wuji_bridge3_20260922','hand=wuji_paper_official_actuator'],
        train='wujiAcquisitionSAPG',seed=args.seed)
    env,player=make_player(cfg,teacher)
    assert not env.eval_mode and env.num_envs==args.num_envs
    assert float(env.cfg['env']['supportActionSpan'])==.04
    assert float(env.cfg['env']['thumbActionStep'])==.025
    model=player.model.eval();before_teacher=tensor_digest(model.state_dict())
    for param in model.parameters():
        param.requires_grad_(False)
    with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
        student=TargetStudent(artifact['feature_mean'],artifact['feature_scale']).to(player.device).eval()
        student.load_state_dict(artifact['state_dict'])
    before_student=tensor_digest(student.state_dict())
    optimizer=torch.optim.Adam(student.parameters(),lr=args.lr)
    if args.restore_optimizer:
        assert artifact.get('optimizer',{}).get('state')
        optimizer.load_state_dict(artifact['optimizer'])
        for group in optimizer.param_groups:group['lr']=args.lr
    initial_optimizer_steps=[int(v['step']) for v in optimizer.state.values()]
    if not initial_optimizer_steps:initial_optimizer_steps=[0]*len(list(student.parameters()))
    assert len(set(initial_optimizer_steps))==1
    parent=artifact.get('dagger',{})
    parent_physics=parent.get('cumulative_student_physics_transitions',parent.get('checks',{}).get('student_physics_transitions',0))
    generator=torch.Generator(device=player.device);generator.manual_seed(args.seed+1000)
    with np.load(args.data) as z:
        mask=z['training'];fx=z['features'][:,:,mask].reshape(-1,116)
        fy=z[arm][:,:,mask].reshape(-1,20)
    assert len(fx)==71640
    fixed_x=torch.tensor(fx,device=player.device);fixed_y=torch.tensor(fy,device=player.device)
    loss_scales=fixed_x.new_tensor([1.]*16+[args.thumb_loss_scale]*4)
    capacity=args.replay_capacity
    assert capacity>=16*args.num_envs
    replay_x=torch.empty((capacity,116),device=player.device)
    replay_y=torch.empty((capacity,20),device=player.device)
    cursor=size=0
    checks=dict(student_physics_transitions=0,teacher_label_rows=0,privileged_input_invariance=0,
        pre_physics_action_matches=0,actual_optimizer_steps=0,resets=0,replay_wraps=0,
        replay_written_rows=0,label_mapping_rows=0,actual_target_max_error=0.)
    expected={};original_pre=env.pre_physics_step
    def pre(action):
        original_pre(action)
        assert torch.equal(env.actions,expected['student_action'])
        error=float((env.cur_targets[:,:20]-expected['applied_target']).abs().max())
        assert error<1e-6,error
        checks['actual_target_max_error']=max(checks['actual_target_max_error'],error)
        checks['pre_physics_action_matches']+=env.num_envs
    env.pre_physics_step=pre
    obs=player.env_reset(player.env)
    state=dict(status='running',started=now(),arm=arm,updates_completed=0,updates_budget=args.updates,
        initial_sha256=artifact_sha,initial_tensor_sha256=before_student,teacher_sha256=teacher_sha,
        teacher_tensor_sha256=before_teacher,seed=args.seed,num_envs=args.num_envs,
        rollout_steps=16,optimizer_batches_per_rollout=8,batch=1024,learning_rate=args.lr,
        replay_capacity=capacity,fixed_fraction=.5,fixed_labels=len(fx),checks=checks,
        thumb_loss_scale=args.thumb_loss_scale,loss_scales=loss_scales.cpu().tolist(),
        optimizer_restored=args.restore_optimizer,initial_optimizer_steps=initial_optimizer_steps,
        parent_student_physics_transitions=parent_physics,
        resume_scope='Model/normalizer and optionally Adam restored; fresh simulator, RNN and FIFO. Not bitwise continuation.',
        scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    atomic_json(args.output/'status.json',state)
    def save(update):
        path=args.output/f'{arm}-update{update:04d}.pth'
        payload={k:v for k,v in artifact.items() if k not in ['state_dict','optimizer','update']}
        payload.update(state_dict={k:v.detach().cpu().clone() for k,v in student.state_dict().items()},
            optimizer=optimizer.state_dict(),update=update,dagger=state.copy())
        torch.save(payload,path)
        atomic_json(path.with_suffix('.json'),dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            update=update,arm=arm,physics_transitions=checks['student_physics_transitions']))
    try:
        save(0)
        for u in range(1,args.updates+1):
            new_x=[];new_y=[]
            for step in range(16):
                with torch.no_grad():
                    initial=env.init_targets[:,:20];current=env.cur_targets[:,:20]
                    lower,upper=env.hand_dof_lower_limits,env.hand_dof_upper_limits
                    x=features(obs,initial,lower,upper)
                    prediction=student(x)
                    action,_=action_from_prediction(prediction,initial,current,lower,upper,arm)
                    # Teacher memory follows the same actual observations and
                    # previous student actions; labels are counterfactual commands.
                    label_action=player.get_action(obs,is_deterministic=True)
                    target=initial+.04*label_action
                    target[:,16:]=current[:,16:]+.025*label_action[:,16:]
                    target=torch.maximum(torch.minimum(target,upper),lower)
                    assert torch.equal(current,env.prev_targets[:,:20])
                    assert torch.equal(target,env.actions_to_targets(label_action))
                    checks['label_mapping_rows']+=env.num_envs
                    delta=target-initial
                    if arm=='incremental':
                        delta[:,16:]=target[:,16:]-current[:,16:]
                    label=delta/delta.new_tensor(SCALES)
                    assert torch.isfinite(x).all() and torch.isfinite(label).all() and torch.isfinite(action).all()
                    if args.runtime_check or checks['student_physics_transitions']==0:
                        changed=obs.clone();changed[:,111:137]+=10.
                        other_x=features(changed,initial,lower,upper)
                        assert torch.equal(x,other_x)
                        other,_=action_from_prediction(student(other_x),initial,current,lower,upper,arm)
                        assert torch.equal(action,other)
                        checks['privileged_input_invariance']+=env.num_envs
                    new_x.append(x.clone());new_y.append(label.clone())
                    expected['student_action']=action.clone()
                    expected['applied_target']=env.actions_to_targets(action).clone()
                    obs,_,done,_=player.env_step(player.env,action)
                    checks['resets']+=int(done.sum())
                    reset_done_rnn_states(player,done)
                    checks['student_physics_transitions']+=env.num_envs
                    checks['teacher_label_rows']+=env.num_envs
            new_x=torch.cat(new_x);new_y=torch.cat(new_y);count=len(new_x)
            slots=(torch.arange(count,device=player.device)+cursor)%capacity
            replay_x[slots]=new_x;replay_y[slots]=new_y
            assert torch.equal(replay_x[slots],new_x) and torch.equal(replay_y[slots],new_y)
            assert replay_x.data_ptr()!=new_x.data_ptr() and replay_y.data_ptr()!=new_y.data_ptr()
            checks['replay_written_rows']+=count
            if cursor+count>=capacity:
                checks['replay_wraps']+=1
            cursor=(cursor+count)%capacity;size=min(size+count,capacity)
            losses=[]
            for _ in range(8):
                ri=torch.randint(size,(512,),device=player.device,generator=generator)
                fi=torch.randint(len(fixed_x),(512,),device=player.device,generator=generator)
                bx=torch.cat([replay_x[ri],fixed_x[fi]])
                by=torch.cat([replay_y[ri],fixed_y[fi]])
                optimizer.zero_grad(set_to_none=True)
                loss=F.smooth_l1_loss(student(bx)*loss_scales,by*loss_scales,beta=.05)
                assert torch.isfinite(loss)
                loss.backward();grad=torch.nn.utils.clip_grad_norm_(student.parameters(),1.)
                assert torch.isfinite(grad)
                optimizer.step();checks['actual_optimizer_steps']+=1;losses.append(float(loss))
            state.update(updates_completed=u,heartbeat=now(),replay_size=size,latest_loss=sum(losses)/len(losses),
                cumulative_student_physics_transitions=parent_physics+checks['student_physics_transitions'])
            atomic_json(args.output/'status.json',state)
            if u in [1,25,100,250,500,1000,args.updates]:
                save(u)
        assert tensor_digest(model.state_dict())==before_teacher
        assert checks['student_physics_transitions']==args.updates*16*args.num_envs
        assert checks['teacher_label_rows']==checks['pre_physics_action_matches']==checks['student_physics_transitions']
        assert torch.equal(student.feature_mean,torch.tensor(artifact['feature_mean'],device=player.device))
        assert torch.equal(student.feature_scale,torch.tensor(artifact['feature_scale'],device=player.device))
        final_optimizer_steps=[int(v['step']) for v in optimizer.state.values()]
        assert all(v==initial_optimizer_steps[0]+checks['actual_optimizer_steps'] for v in final_optimizer_steps)
        state['final_optimizer_steps']=final_optimizer_steps
        if args.lr==0:
            assert tensor_digest(student.state_dict())==before_student
        else:
            assert tensor_digest(student.state_dict())!=before_student
        state.update(status='completed',finished=now(),teacher_unchanged=True,normalizer_unchanged=True)
    except BaseException as e:
        state.update(status='failed',finished=now(),error=repr(e));raise
    finally:
        atomic_json(args.output/'status.json',state)
    print(json.dumps(state))


if __name__=='__main__':
    main()
