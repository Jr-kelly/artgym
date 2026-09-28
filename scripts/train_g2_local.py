"""Small privileged PPO for the real-acquisition local task (not grasp RL).

Fixed feature scaling, Gaussian exploration, bounded motor residual, GAE PPO.
Episode max errors are independent from reward. Timeout is a finite-horizon
task terminal; every failure remains in the denominator. Checkpoints atomic.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import time

from scripts.g2_local_env import LocalG2, ROOT
import numpy as np
import torch
from torch import nn
from torch.distributions import Normal


class ActorCritic(nn.Module):
    def __init__(self, obs_dim, action_dim):
        super().__init__()
        self.actor = nn.Sequential(nn.Linear(obs_dim, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, action_dim))
        self.critic = nn.Sequential(nn.Linear(obs_dim, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 1))
        self.logstd = nn.Parameter(torch.full((action_dim,), -1.5))
        for layer in list(self.actor)+list(self.critic):
            if isinstance(layer, nn.Linear):
                nn.init.orthogonal_(layer.weight, np.sqrt(2))
                nn.init.zeros_(layer.bias)
        nn.init.orthogonal_(self.actor[-1].weight, .01)
        nn.init.orthogonal_(self.critic[-1].weight, 1.)

    def forward(self, obs):
        return Normal(self.actor(obs), self.logstd.clamp(-3.5, .0).exp()), self.critic(obs).squeeze(-1)

    def mean_action(self, obs):
        return self.actor(obs).clamp(-1, 1)


def expand_support_checkpoint(model, saved):
    """Exact support function preservation; zero-initialize added thumb output.

    Feature order: base84, residual16/20, previous_action16/20.
    No claim of imitation/success data: simply warm-start the shared network.
    """
    state = model.state_dict()
    for key, old in saved['model'].items():
        if old.shape == state[key].shape:
            state[key].copy_(old)
        elif key in ['actor.0.weight', 'critic.0.weight']:
            state[key].zero_()
            state[key][:, :100] = old[:, :100]
            state[key][:, 104:120] = old[:, 100:116]
        elif key in ['actor.4.weight', 'actor.4.bias']:
            state[key].zero_()
            state[key][:16] = old
        elif key == 'logstd':
            state[key][:16] = old
        else:
            raise ValueError('Unexpected checkpoint expansion: '+key)
    model.load_state_dict(state)


def main():
    process_start = time.monotonic()
    p = argparse.ArgumentParser()
    p.add_argument('--task-variant',choices=['legacy','v2-grip','v2-prefix-grip'],default='legacy')
    p.add_argument('--task', choices=['H','S'], default='H')
    p.add_argument('--route', choices=['support','joint'], default='support')
    p.add_argument('--num-envs', type=int, default=64)
    p.add_argument('--updates', type=int, default=1000)
    p.add_argument('--horizon', type=int, default=64)
    p.add_argument('--epochs', type=int, default=4)
    p.add_argument('--minibatch', type=int, default=2048)
    p.add_argument('--lr', type=float, default=3e-4)
    p.add_argument('--seed', type=int, default=928)
    p.add_argument('--hours', type=float, default=2.)
    p.add_argument('--eval-every', type=int, default=50)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--resume-optimizer', action='store_true', help='Continue the same training configuration and Adam state')
    p.add_argument('--thumb-plan',type=Path,help='Declared routeB kinematic thumb motor prior, replacing frozen thumb actor')
    p.add_argument('--initial-support-std',type=float)
    p.add_argument('--initial-thumb-std',type=float)
    p.add_argument('--teacher', type=Path, default=Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/release-core-teacher-student-20260924-v1/wuji-core-teacher-student-20260924-teacher.pth'))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'config.json').write_text(json.dumps({k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},indent=2)+'\n')
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.set_num_threads(1)
    saved=torch.load(args.checkpoint,map_location='cuda:0') if args.checkpoint else None
    plan=json.loads(args.thumb_plan.read_text()) if args.thumb_plan else (saved.get('thumb_plan') if saved else None)
    if args.task_variant=='v2-prefix-grip':
        from scripts.g2_v2_prefix_grip_env import PrefixGripV2
        env=PrefixGripV2(args.task,args.num_envs,args.route)
    elif args.task_variant=='v2-grip':
        from scripts.g2_v2_grip_env import GripV2
        env=GripV2(args.task,args.num_envs,args.route)
    else:env = LocalG2(args.task, args.num_envs, args.route)
    if plan is not None:
        assert args.task=='S' and args.route=='joint'
        env.thumb_plan=plan
    if args.task == 'S' and plan is None:
        from scripts.g2_local_teacher import BatchedTeacher
        env.teacher = BatchedTeacher(env, args.teacher, 'cuda:0')
    obs = env.observation().cuda()
    model = ActorCritic(obs.shape[-1], env.action_dim).cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    if args.checkpoint:
        if saved['action_dim'] == 16 and env.action_dim == 20:
            if args.resume_optimizer:
                raise ValueError('Expanded joint controller requires a new optimizer')
            expand_support_checkpoint(model, saved)
        else:
            model.load_state_dict(saved['model'])
        if args.resume_optimizer:
            optimizer.load_state_dict(saved['optimizer'])
    with torch.no_grad():
        for value, indices in [(args.initial_support_std,slice(0,16)),(args.initial_thumb_std,slice(16,20))]:
            if value is not None:
                assert not args.resume_optimizer and .03 <= value <= 1.
                model.logstd[indices]=np.log(value)
    stopping = [False]
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, lambda *_: stopping.__setitem__(0, True))
    clock = process_start
    # Session deadline includes scene/model setup; reserve final90min for delivery.
    task_state = ROOT/'runs/g2-local-policy-20260928/state.json'
    deadline = clock+args.hours*3600
    if task_state.exists() and args.task_variant=='legacy':
        import datetime
        state = json.loads(task_state.read_text())
        delivery = datetime.datetime.fromisoformat(state['delivery_start_utc']).timestamp()
        deadline = min(deadline,time.monotonic()+max(0,delivery-time.time()))
    transitions, episodes, best = 0, 0, -1e10
    curve = (args.output/'learning.jsonl').open('a', buffering=1)
    episodic = (args.output/'training-episodes.jsonl').open('a', buffering=1)
    obs_buf = torch.zeros(args.horizon, env.n, obs.shape[-1], device='cuda')
    act_buf = torch.zeros(args.horizon, env.n, env.action_dim, device='cuda')
    log_buf = torch.zeros(args.horizon, env.n, device='cuda')
    val_buf, rew_buf, done_buf = log_buf.clone(), log_buf.clone(), log_buf.clone()
    ep_returns = torch.zeros(env.n)
    update = 0
    completed_updates = 0
    evaluation_rows = None
    evaluation_update = None
    error = None

    class StopTraining(Exception):
        pass

    def check_stop():
        if stopping[0] or time.monotonic()>=deadline:
            stopping[0] = True
            raise StopTraining()

    def save(name):
        path = args.output/name
        torch.save(dict(model=model.state_dict(), optimizer=optimizer.state_dict(), update=completed_updates,
            update_attempt=update,
            transitions=transitions, episodes=episodes, learning_elapsed_seconds=time.monotonic()-clock,
            obs_dim=obs.shape[-1], action_dim=env.action_dim, task=args.task, route=args.route,
            source=('configs/g2_local/'+args.task+'-actual-state.npz' if args.task_variant=='legacy' else str(env.metadata.get('knife_relative_urdf'))),
            method='new privileged PPO motor residual; original weights unchanged',task_variant=args.task_variant,
            asset_urdf=env.metadata.get('knife_relative_urdf'),
            data_source={'v2-grip':'configs/g2_functional_v2/grip-local-v1','v2-prefix-grip':'configs/g2_functional_v2/grip-prefix-v2'}.get(args.task_variant),
            thumb_plan=env.thumb_plan,
            action_mapping=('all20 motor references: source closed target + absolute .20rad residual, slew .02rad/control' if args.task_variant!='legacy' else 'support16 absolute+slew; joint thumb4 uses .20rad absolute residual around IK prior or .025rad incremental correction around teacher; total thumb step capped .025rad'),
            terminal_return='absorbing -8/step gamma.995 through finite horizon'), str(path)+'.tmp')
        os.replace(str(path)+'.tmp', path)

    try:
        for update in range(1, args.updates+1):
            batch_start = time.monotonic()
            ended = []
            for step in range(args.horizon):
                check_stop()
                with torch.no_grad():
                    dist, value = model(obs)
                    action = dist.sample()
                    logprob = dist.log_prob(action).sum(-1)
                obs_buf[step], act_buf[step], log_buf[step], val_buf[step] = obs, action, logprob, value
                next_obs, reward, done, info = env.step(action)
                rew_buf[step], done_buf[step] = reward.cuda(), done.float().cuda()
                ep_returns += reward
                ids = done.nonzero(as_tuple=False).squeeze(-1)
                if len(ids):
                    metrics = env.metrics()
                    for idx in ids.tolist():
                        row = {k:v[idx].tolist() for k,v in metrics.items()}
                        row.update(update=update, env=idx, episode=episodes, length=int(env.age[idx]),
                                   reward=float(ep_returns[idx]), scope='training rollout, not independent evaluation')
                        episodic.write(json.dumps(row)+'\n')
                        ended.append(row)
                        episodes += 1
                    ep_returns[ids] = 0
                    next_obs = env.reset(ids)
                obs = next_obs.cuda()
                transitions += env.n
            with torch.no_grad():
                _, next_value = model(obs)
            advantage = torch.zeros_like(rew_buf)
            gae = torch.zeros(env.n, device='cuda')
            for step in reversed(range(args.horizon)):
                following = next_value if step == args.horizon-1 else val_buf[step+1]
                live = 1-done_buf[step]
                delta = rew_buf[step] + .995 * following * live - val_buf[step]
                gae = delta + .995 * .95 * live * gae
                advantage[step] = gae
            returns = advantage+val_buf
            flat_obs, flat_act = obs_buf.flatten(0,1), act_buf.flatten(0,1)
            flat_log, flat_adv, flat_return = log_buf.flatten(), advantage.flatten(), returns.flatten()
            flat_adv = (flat_adv-flat_adv.mean())/(flat_adv.std()+1e-8)
            losses, kls = [], []
            for epoch in range(args.epochs):
                check_stop()
                order = torch.randperm(len(flat_obs),device='cuda')
                for batch in order.split(args.minibatch):
                    dist, value = model(flat_obs[batch])
                    logp = dist.log_prob(flat_act[batch]).sum(-1)
                    ratio = (logp-flat_log[batch]).exp()
                    pi_loss = -torch.minimum(ratio*flat_adv[batch], ratio.clamp(.8,1.2)*flat_adv[batch]).mean()
                    value_loss = .5*(value-flat_return[batch]).square().mean()
                    entropy = dist.entropy().sum(-1).mean()
                    loss = pi_loss+.5*value_loss-.002*entropy
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(),1.)
                    optimizer.step()
                    losses.append(float(loss.detach()))
                    kls.append(float(((ratio-1)-(logp-flat_log[batch])).mean().detach()))
                if np.mean(kls[-max(1, len(order)//args.minibatch):])>.03:
                    break
            elapsed = time.monotonic()-clock
            completed_updates = update
            row = dict(update=update, transitions=transitions, training_episodes=episodes,
                elapsed_seconds=elapsed, end_to_end_transitions_per_second=transitions/elapsed,
                update_seconds=time.monotonic()-batch_start, reward=float(rew_buf.mean()),
                loss=float(np.mean(losses)), kl=float(np.mean(kls)), std=float(model.logstd.exp().mean()),
                completed_in_update=len(ended), recent_success=sum(v['success'] for v in ended)/len(ended) if ended else None)
            curve.write(json.dumps(row)+'\n')
            print(json.dumps(row), flush=True)
            # Deterministic evaluations are separate from sampled training episodes.
            # These all reuse one development state; N replicas are NOT N placements.
            if update in [1, 10] or update % args.eval_every == 0:
                save('checkpoint-%05d.pth'%update)
                interrupted = int((env.age>0).sum())
                evaluation_start = time.monotonic()
                env.reset()
                if hasattr(env,'prefix_end'):
                    np.savez_compressed(args.output/('prefix-end-%05d.npz'%update),**env.prefix_end)
                evaluation_rows = []
                evaluation_update = update
                for frame_idx in range(env.steps):
                    check_stop()
                    with torch.no_grad():
                        act = model.mean_action(env.observation().cuda())
                    env.step(act)
                    # Preserve every evaluation replica, including failures.
                    frame = env.frame()
                    frame.update(env.contacts_for_evaluation())
                    evaluation_rows.append(frame)
                metric = {k:v.tolist() for k,v in env.metrics().items()}
                evaluation = dict(update=update, scope='deterministic development reset, one acquisition source',
                    replicas=env.n, unique_acquisition_states=1, metrics=metric,
                    training_partial_episodes_interrupted=interrupted,
                    elapsed_seconds=time.monotonic()-evaluation_start)
                (args.output/('eval-%05d.json'%update)).write_text(json.dumps(evaluation,indent=2)+'\n')
                np.savez_compressed(args.output/('eval-%05d.npz'%update),
                    **{k:np.asarray([v[k] for v in evaluation_rows]) for k in evaluation_rows[0]})
                evaluation_rows = None
                success = float(np.mean(metric['success']))
                quality = success*100 - float(np.mean(metric['world_rotation_rad'])) - 10*float(np.mean(metric['world_drift_m']))
                if args.task_variant!='legacy':
                    quality=success*100-float(np.mean(metric['hand_relative_rotation_rad']))-10*float(np.mean(metric['short_lift_tracking_error_m']))+10*float(np.mean(metric['minimum_hold_rise_m']))
                if args.task == 'S':
                    quality -= 25*float(np.mean(metric['endpoint_max_errors_m']))
                if quality > best:
                    best = quality
                    save('best-development.pth')
                print(json.dumps(dict(evaluation_update=update, success=success, selection_score=quality,
                    max_rotation_mean=float(np.mean(metric['world_rotation_rad'])))),flush=True)
                ep_returns.zero_()
                obs = env.reset().cuda()
            if update % 10 == 0:
                save('last.pth')
            if stopping[0] or elapsed>=args.hours*3600:
                break
        save('last.pth')
    except StopTraining:
        save('last.pth')
    except BaseException as exc:
        error = repr(exc)
        save('interrupted.pth')
        raise
    finally:
        if evaluation_rows:
            np.savez_compressed(args.output/('eval-%05d-partial.npz'%evaluation_update),
                **{k:np.asarray([v[k] for v in evaluation_rows]) for k in evaluation_rows[0]})
        (args.output/'status.json').write_text(json.dumps(dict(pid=os.getpid(), status='error' if error else ('stopped' if stopping[0] else 'finished'),
            error=error, update=completed_updates, update_attempt=update, transitions=transitions, episodes=episodes,
            seconds=time.monotonic()-clock),indent=2)+'\n')
        curve.close()
        episodic.close()
        env.close()


if __name__ == '__main__':
    main()
