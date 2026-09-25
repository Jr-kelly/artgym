"""Fixed-weight policy response to equivalent quaternion signs and asset frames.

Use only saved training-source observations, identical zero RNN states and no
physics transitions. No optimization or normalizer update is performed. These
action differences isolate input convention sensitivity, not task success.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
import numpy as np
import torch
from scipy.spatial.transform import Rotation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    checkpoint = base / 'verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    observations = base / 'diagnostics/functional20-runtime-v2/observations.npz'
    source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
    reference = np.load(source)[0, 43:47]
    raw = np.load(observations)['observations'][:256]
    assert raw.shape == (256, 137)
    cfg = configuration('wuji_acquisition_official_timed2', 256,
                        ['hand=wuji_paper_official_actuator',
                         'object=knife_wuji_lowgain_functional20_20260922', 'test=True'],
                        train='wujiAcquisitionSAPG', seed=20261032)
    env, player = make_player(cfg, checkpoint)
    model = player.model
    model.eval()
    original = {name: value.clone() for name, value in model.state_dict().items()}
    batch = torch.as_tensor(raw, device=player.device)
    converted = original_to_acquisition_observations(batch[:, :111], batch[:, 111:132])
    signed = align_quaternion_hemisphere(*converted, reference)
    states = dict(raw=(batch[:, :111], batch[:, 111:132]), acquisition=converted, acquisition_hemisphere=signed)
    # A physically equivalent arbitrary sign flip must collapse to exactly the
    # same adapted observation and rotation, without modifying any other field.
    flip_policy, flip_privileged = (value.clone() for value in converted)
    for value, starts in [(flip_policy, [23, 30]), (flip_privileged, [3, 10])]:
        for start in starts:
            value[:, start:start+4] *= -1
    equiv = align_quaternion_hemisphere(flip_policy, flip_privileged, reference)
    assert all(torch.equal(x, y) for x, y in zip(equiv, signed))
    for before, after, starts in [(converted[0], signed[0], [23, 30]), (converted[1], signed[1], [3, 10])]:
        mask = torch.ones(before.shape[1], dtype=torch.bool, device=before.device)
        for start in starts:
            mask[start:start+4] = False
            a, b = before[:, start:start+4].cpu().numpy(), after[:, start:start+4].cpu().numpy()
            assert np.max(abs(Rotation.from_quat(a).as_matrix() - Rotation.from_quat(b).as_matrix())) < 1e-12
        assert torch.equal(before[:, mask], after[:, mask])
    results = {}
    try:
        for name, (policy, privileged) in states.items():
            obs = torch.cat([policy, privileged, batch[:, 132:], torch.full((len(batch), 1), 50., device=player.device)], dim=1)
            with torch.no_grad():
                result = model(dict(is_train=False, prev_actions=None, obs=obs,
                                    rnn_states=[state.clone().zero_() for state in player.states]))
            rms = model.running_mean_std
            normalized = (obs[:, :137] - rms.running_mean) / torch.sqrt(rms.running_var + rms.epsilon)
            results[name] = dict(mu=result['mus'].clone(), sigma=result['sigmas'].clone(),
                                 clipped_policy_input_fraction=float((normalized[:, :111].abs() > 5).float().mean()),
                                 clipped_privileged_input_fraction=float((normalized[:, 111:132].abs() > 5).float().mean()))
        comparisons = []
        for a, b in [('raw', 'acquisition'), ('acquisition', 'acquisition_hemisphere'), ('raw', 'acquisition_hemisphere')]:
            x, y = results[a], results[b]
            kl = torch.distributions.kl_divergence(torch.distributions.Normal(x['mu'], x['sigma']),
                                                 torch.distributions.Normal(y['mu'], y['sigma'])).sum(-1)
            delta = (x['mu'].clamp(-1, 1) - y['mu'].clamp(-1, 1)).abs()
            comparisons.append(dict(before=a, after=b, gaussian_kl_mean=float(kl.mean()),
                                    clipped_action_abs_change_mean=float(delta.mean()),
                                    clipped_thumb_abs_change_mean=float(delta[:, 16:].mean())))
        assert all(torch.equal(model.state_dict()[name], value) for name, value in original.items())
        report = dict(status='verified', scope=__doc__, same_rotations_verified=True,
                      arbitrary_sign_flip_invariance_verified=True, non_quaternion_fields_unchanged=True,
                      model_and_normalizer_unchanged=True, observations=256,
                      conditions={name: {k: v for k, v in row.items() if k not in ['mu', 'sigma']} for name, row in results.items()},
                      comparisons=comparisons, negative_converted_initial_dot=int(((converted[0][:, 23:27] * torch.as_tensor(reference, device=player.device)).sum(-1) < 0).sum()),
                      files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             [checkpoint, observations, source, Path(__file__), root / 'scripts/wuji_quaternion_hemisphere.py']})
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
