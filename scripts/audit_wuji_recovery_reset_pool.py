"""Enumerate every training reset under zero action; preserve physical failures."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.utils.utils import set_seed
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--states', help='Explicit training-only pool; default is original frozen pool.')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    seed = 2026093092
    set_seed(seed)
    overrides = ['object=knife_wuji_reference',
        'hand=wuji_paper_official_actuator', 'task.env.episodeLength=600',
        'task.env.goalSwitchTimeoutSec=0.0', 'task.env.maxConsecutiveSuccesses=0']
    if a.states:
        overrides.append('task.env.trainingStates=' + a.states)
    cfg = configuration(a.task, 512, overrides,
        train='wujiArtManipReferenceSAPG', seed=seed)
    (a.output / 'resolved.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env = make_env(cfg)
    assert len(env.all_valid_states) == 512

    def fixed_samples(ids):
        env.source_ids[ids] = ids // 128
        env.source_visits += torch.bincount(ids // 128, minlength=4)
        return env.all_valid_states[ids].clone()

    env.sample_grasps = fixed_samples
    env.reset()
    initial_targets = env.prev_targets.clone()
    periods = env.clock_period.clone() if hasattr(env, 'clock_period') else None
    clock_verified = False
    max_map_error = 0.
    original = env.compute_reward
    active = torch.ones(512, dtype=torch.bool, device=env.device)
    trace = []

    def capture(actions):
        original(actions)
        drift = torch.linalg.vector_norm(env.object_pos - env.init_object_pos, dim=-1)
        angle = 2 * torch.asin(torch.linalg.vector_norm(
            quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))[:, :3],
            dim=-1).clamp(0, 1))
        trace.append(dict(drift=drift.cpu().numpy(), rotation=angle.cpu().numpy(),
            active=active.cpu().numpy().copy(), done=env.reset_buf.cpu().numpy().copy(),
            invalid=env.truncated_envs.cpu().numpy().copy()))
        active.logical_and_(env.reset_buf == 0)

    env.compute_reward = capture
    try:
        for step in range(600):
            _, reward, _, info = env.step(env.zero_actions())
            assert torch.isfinite(reward).all()
            max_map_error = max(max_map_error, float((env.prev_targets - initial_targets).abs().max()))
            if periods is not None:
                assert float(info['holding/max_abs_additional_reward']) <= 25.00001
                if step == 598:
                    assert torch.equal(env.clock_switches[active], torch.where(periods[active] == 60, 9, 3))
                    clock_verified = True
                if step == 599:
                    assert (env.clock_switches[env.progress_buf == 0] == 0).all()
    finally:
        env.gym.destroy_sim(env.sim)
    t = {k: np.stack([row[k] for row in trace]) for k in trace[0]}
    np.savez_compressed(a.output / 'trace.npz', **t)
    stable = (t['drift'] < .01) & (t['rotation'] < .25) & t['active'] & ~t['invalid']
    rows = []
    for source in range(4):
        sl = slice(source * 128, (source + 1) * 128)
        rows.append(dict(source=source, n=128, body_1sec=int(stable[:30, sl].all(0).sum()),
            body_20sec=int(stable[:, sl].all(0).sum()),
            bad_pool_rows=(np.flatnonzero(~stable[:, sl].all(0)) + source * 128).tolist()))
    bad = np.flatnonzero(~stable.all(0))
    result = dict(task=a.task, seed=seed, rows=rows,
        max_target_change=max_map_error, clock_schedule_verified=clock_verified,
        bad_first_steps={str(i): int(np.flatnonzero(~stable[:, i])[0] + 1) for i in bad},
        training_states_sha256=env.training_states_sha256,
        trace_sha256=hashlib.sha256((a.output / 'trace.npz').read_bytes()).hexdigest(),
        scope='All512 frozen training rows, one per environment, zero hand action. '
        'Goal timeout and success-budget reset disabled for20s physical diagnostic; '
        'physical invalid/fall termination unchanged. Capture before resets. No filtering or learned skill claim.')
    (a.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
