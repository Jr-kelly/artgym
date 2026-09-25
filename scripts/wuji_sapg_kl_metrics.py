"""Separate SAPG exploration relabeling from on-policy Gaussian movement.

Call after calc_gradients: its returned distributions were computed before the
current optimizer step. Dataset reference distributions may be refreshed after
minibatches, so these are not whole-epoch rollout-to-final-policy distances.
"""
import torch
from rl_games.algos_torch import torch_ext


def split_kl(mu, sigma, old_mu, old_sigma, rnn_masks, off_policy_mask, reported):
    with torch.no_grad():
        upstream = torch_ext.policy_kl(mu, sigma, old_mu, old_sigma, False)
        weights = torch.ones_like(upstream) if rnn_masks is None else rnn_masks.reshape(-1)
        valid = weights > 0
        off = off_policy_mask.reshape(-1).bool()
        assert upstream.shape == weights.shape == off.shape
        reconstructed = (upstream * weights).sum() / weights.numel()
        assert torch.allclose(reconstructed, reported, atol=1e-6, rtol=1e-6)
        new_mu, new_sigma = mu.double(), sigma.double()
        old_mu, old_sigma = old_mu.double(), old_sigma.double()
        assert (new_sigma > 0).all() and (old_sigma > 0).all()
        exact = (torch.log(old_sigma / new_sigma) +
                 (new_sigma.square() + (old_mu - new_mu).square()) /
                 (2 * old_sigma.square()) - .5).sum(-1)
        assert torch.isfinite(exact).all()
        row = dict(reported_aggregate_kl=float(reported), total_samples=int(valid.sum()))
        for name, mask in [('on', valid & ~off), ('off', valid & off)]:
            values = exact[mask]
            count = int(mask.sum())
            row[name] = dict(count=count, exact_mean=float(values.mean()) if count else None,
                             exact_maximum=float(values.max()) if count else None,
                             upstream_mean=float(upstream[mask].mean()) if count else None)
        return row


def summarize_epochs(records):
    result = []
    for epoch in sorted({row['epoch'] for row in records}):
        rows = [row for row in records if row['epoch'] == epoch]
        summary = dict(epoch=epoch, minibatches=len(rows),
                       reported_aggregate_mean=sum(row['reported_aggregate_kl'] for row in rows) / len(rows))
        for name in ['on', 'off']:
            count = sum(row[name]['count'] for row in rows)
            summary[name] = dict(count=count,
                exact_mean=sum(row[name]['exact_mean'] * row[name]['count'] for row in rows if row[name]['count']) / count if count else None,
                exact_maximum=max(row[name]['exact_maximum'] for row in rows if row[name]['count']) if count else None)
        result.append(summary)
    return result
