"""CPU replay of original expert labels verifies the shadow-player interface."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not torch.cuda.is_available(), 'Run with CUDA_VISIBLE_DEVICES empty; this is a CPU check'
    cfg = configuration('wuji_multigrasp', 1, ['object=knife_wuji_bridge3_20260922',
        'hand=wuji_paper_official_actuator'], train='wujiAcquisitionSAPG', seed=2026093051)
    cfg.rl_device = 'cpu'
    records = []
    for source, name in [(0, 'historical'), (3, 'source3')]:
        checkpoint = Path(f'runs/unified-policy-20260930/experts/{name}.pth')
        path = Path(f'runs/unified-policy-20260930/train-data-t5/source{source}/sequences.npz')
        with np.load(path) as z:
            data = {k: z[k][:, :4] for k in ['obs', 'mu', 'done']}
        player = build_policy_player(cfg, preprocess_train_config(cfg,
            OmegaConf.to_container(cfg.train, resolve=True)), checkpoint, _infer_expl_num_blocks(checkpoint), 0)
        init_player_rnn_for_batch(player, 4)
        captured = {}
        def capture(module, inputs, output):
            captured['mu'] = output['mus'].detach().cpu().numpy()
        player.model.register_forward_hook(capture)
        maximum, squared, count, step_errors = 0., 0., 0, []
        for t in range(600):
            player.get_action(torch.as_tensor(data['obs'][t]), is_deterministic=True)
            error = captured['mu'] - data['mu'][t]
            maximum = max(maximum, float(np.max(np.abs(error))))
            step_errors.append(float(np.max(np.abs(error))))
            executed = np.clip(captured['mu'], -1, 1) - np.clip(data['mu'][t], -1, 1)
            squared += float(np.square(executed).sum())
            count += executed.size
            ids = np.flatnonzero(data['done'][t])
            for state in player.states:
                state[:, ids, :] = 0
        records.append(dict(source=source, steps=600, trajectories=4, max_mu_error=maximum,
            executed_action_rmse=(squared / count) ** .5, step_max_errors=step_errors,
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest()))
    args.output.write_text(json.dumps(dict(records=records, exact_replay_passed=all(r['max_mu_error']<1e-4 for r in records),
        same_device_replay_required=True,
        scope='CPU replay versus recorded GPU means. The initial strict1e-4 check failed; retain numerical discrepancy. This does not authorize new labels; collector requires same-device full-history replay<1e-5 and handover availability.'), indent=2) + '\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='step_max_errors'} for r in records]))


if __name__ == '__main__':
    main()
