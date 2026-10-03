"""Damp an Adam actor proposal to an analytic rollout KL bound.

Actor and critic are separate networks. Critic updates are retained; an actor
proposal that cannot meet the bound restores both its parameters and Adam state.
Accepted damping is equivalent to scaling this Adam parameter step, while its
new moments remain valid. The bound concerns the current sampled rollout only.
"""
import copy
import torch


def rollout_kl(model, public, old_mean, old_scale, active, chunk=4096):
    total = torch.zeros((), device=public.device)
    count = active.sum()
    if not count:
        return 0.
    with torch.no_grad():
        scale = model.logstd.clamp(-3.5, -.4).exp()
        for first in range(0, len(public), chunk):
            selected = active[first:first+chunk]
            if not selected.any():
                continue
            mean = model.actor_logits(public[first:first+chunk][selected])
            previous_mean = old_mean[first:first+chunk][selected]
            previous_scale = old_scale[first:first+chunk][selected]
            kl = torch.log(scale/previous_scale) + (previous_scale.square() + (previous_mean-mean).square())/(2*scale.square()) - .5
            total += kl.sum()
    return float(total/count)


def bounded_step(model, optimizer, public, old_mean, old_scale, active, maximum_kl=.03):
    actor = list(model.actor.parameters()) + [model.logstd]
    critic = list(model.critic.parameters())
    if not active.any():
        # Scripted-prefix batches offer no actor objective. Do not let inherited
        # Adam momentum drift the actor when it never controlled this rollout.
        for p in actor:
            p.grad = None
        torch.nn.utils.clip_grad_norm_(critic, 1.)
        optimizer.step()
        return dict(accepted=False, step_fraction=0., analytic_active_rollout_kl=0., backtracks=0, inactive_rollout=True)
    previous = [p.detach().clone() for p in actor]
    previous_state = [copy.deepcopy(optimizer.state[p]) for p in actor]
    torch.nn.utils.clip_grad_norm_(actor, 1.)
    torch.nn.utils.clip_grad_norm_(critic, 1.)
    optimizer.step()
    proposed = [p.detach().clone() for p in actor]
    factor = 1.
    for trial in range(11):
        with torch.no_grad():
            for p, before, after in zip(actor, previous, proposed):
                p.copy_(before + factor*(after-before))
        divergence = rollout_kl(model, public, old_mean, old_scale, active)
        if divergence <= maximum_kl and torch.isfinite(torch.tensor(divergence)):
            return dict(accepted=True, step_fraction=factor, analytic_active_rollout_kl=divergence, backtracks=trial)
        factor *= .5
    with torch.no_grad():
        for p, before, state in zip(actor, previous, previous_state):
            p.copy_(before)
            optimizer.state[p] = state
    return dict(accepted=False, step_fraction=0., analytic_active_rollout_kl=rollout_kl(model, public, old_mean, old_scale, active), backtracks=11)
