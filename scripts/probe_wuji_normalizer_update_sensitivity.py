"""Measure normalization-only policy drift over two batch sizes and four counts.

This uses training-source observations, frozen CP10 weights, identical zero RNN
states and no physics steps. It is a diagnostic of input preprocessing, not a
claim that a normalization schedule solves manipulation or preserves PPO data.
Report both Gaussian means and clipped control actions to avoid interpreting
unbounded network output as an executed joint command.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    checkpoint = root / 'runs/wuji-goal/verified-policies/teacher-official-timed2-cp10/teacher.pth'
    observations = root / 'runs/wuji-goal/diagnostics/functional20-runtime-v2/observations.npz'
    data = np.load(observations)['observations']
    assert data.shape == (10000, 137)
    cfg = configuration('wuji_acquisition_official_timed2', 256,
                        ['hand=wuji_paper_official_actuator',
                         'object=knife_wuji_lowgain_functional20_20260922', 'test=True'],
                        train='wujiAcquisitionSAPG', seed=20261021)
    env, player = make_player(cfg, checkpoint)
    model = player.model
    original = {key: value.clone() for key, value in model.state_dict().items()}
    batch = torch.as_tensor(data, device=player.device)
    probe = torch.cat([batch[:256], torch.full((256, 1), 50., device=player.device)], dim=1)
    records = []

    def forward():
        model.eval()
        with torch.no_grad():
            return model(dict(is_train=False, prev_actions=None, obs=probe,
                              rnn_states=[value.clone().zero_() for value in player.states]))

    try:
        baseline = forward()
        original_dist = torch.distributions.Normal(baseline['mus'], baseline['sigmas'])
        for size in [256, 8192]:
            for count in [39321601., 1000000., 100000., 1.]:
                model.load_state_dict(original)
                rms = model.running_mean_std
                rms.count.fill_(count)
                rms.train()
                with torch.no_grad():
                    rms(batch[:size])
                result = forward()
                delta = (result['mus'] - baseline['mus']).abs()
                action_delta = (result['mus'].clamp(-1, 1) - baseline['mus'].clamp(-1, 1)).abs()
                kl = torch.distributions.kl_divergence(
                    original_dist, torch.distributions.Normal(result['mus'], result['sigmas'])).sum(-1)
                records.append(dict(update_observations=size, initial_count=count,
                                    new_observation_weight=size / (count + size),
                                    count_after=float(rms.count), gaussian_kl_mean=float(kl.mean()),
                                    gaussian_kl_max=float(kl.max()), unbounded_mu_abs_change_mean=float(delta.mean()),
                                    clipped_action_abs_change_mean=float(action_delta.mean()),
                                    clipped_action_abs_change_max=float(action_delta.max()),
                                    clipped_thumb_abs_change_mean=float(action_delta[:, 16:].mean())))
                for key, value in original.items():
                    if not key.startswith('running_mean_std.'):
                        assert torch.equal(model.state_dict()[key], value), key
        model.load_state_dict(original)
        assert all(torch.equal(model.state_dict()[key], value) for key, value in original.items())
        result = dict(status='completed', scope=__doc__, records=records,
                      probe_observations=256, learned_weights_unchanged=True,
                      all_model_tensors_restored=True, rnn='identical zeros for all conditions',
                      checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                      observations_sha256=hashlib.sha256(observations.read_bytes()).hexdigest(),
                      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output / 'source.py').write_bytes(Path(__file__).read_bytes())
        (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
