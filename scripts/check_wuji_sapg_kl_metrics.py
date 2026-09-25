"""Analytical Gaussian examples exercise absent/present masks and group splits."""
import json
import torch
from scripts.wuji_sapg_kl_metrics import split_kl, summarize_epochs
from rl_games.algos_torch.torch_ext import policy_kl


def main():
    mu = torch.zeros(4, 2)
    old = mu.clone()
    mu[2:] = 1
    sigma = torch.ones_like(mu) * .25
    off = torch.tensor([0, 0, 1, 1], dtype=torch.bool)
    plain = split_kl(mu, sigma, old, sigma, None, off, policy_kl(mu, sigma, old, sigma))
    assert plain['on']['exact_mean'] == 0 and plain['off']['exact_mean'] == 16
    mask = torch.tensor([1., 0., 1., 0.])
    reported = (policy_kl(mu, sigma, old, sigma, False) * mask).sum() / 4
    masked = split_kl(mu, sigma, old, sigma, mask, off, reported)
    assert masked['on']['count'] == masked['off']['count'] == 1
    plain['epoch'] = masked['epoch'] = 1
    summary = summarize_epochs([plain, masked])
    assert summary[0]['on']['count'] == 3 and summary[0]['off']['exact_mean'] == 16
    print(json.dumps(dict(passed=True, plain=plain, masked=masked, summary=summary)))


if __name__ == '__main__':
    main()
