"""CPU old/new heldout-history fit decomposition, not a physical evaluation."""
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
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not torch.cuda.is_available(), 'This diagnostic must run with CUDA_VISIBLE_DEVICES empty'
    torch.set_num_threads(1)
    cfg = configuration('wuji_multigrasp', 1, ['object=knife_wuji_bridge3_20260922',
        'hand=wuji_paper_official_actuator'], train='wujiAcquisitionSAPG', seed=2026093051)
    cfg.rl_device = 'cpu'
    rows = []
    for item in args.models:
        name, checkpoint = item.split('=', 1)
        checkpoint = Path(checkpoint)
        player = build_policy_player(cfg, preprocess_train_config(cfg,
            OmegaConf.to_container(cfg.train, resolve=True)), checkpoint, _infer_expl_num_blocks(checkpoint), 0)
        capture = {}
        def hook(module, inputs, output):
            capture['mu'] = output['mus'].detach().cpu().numpy().copy()
        player.model.register_forward_hook(hook)
        for source in range(4):
            for seconds in [2, 5]:
                directory = args.data / 'aggregate' / f't{seconds}/source{source}'
                with np.load(directory/'sequences.npz') as z:
                    data = {k: z[k][:, 120:] for k in z.files}
                info = json.loads((directory/'interface.json').read_text())
                lower, upper = np.asarray(info['joint_lower']), np.asarray(info['joint_upper'])
                init_player_rnn_for_batch(player, 40)
                predictions = []
                for t in range(600):
                    player.get_action(torch.as_tensor(data['obs'][t]), is_deterministic=True)
                    predictions.append(capture['mu'])
                    ids = np.flatnonzero(data['done'][t])
                    for state in player.states:
                        state[:, ids, :] = 0
                mu = np.stack(predictions)
                action = np.clip(mu, -1, 1)
                raw = data['initial_target'] + action * .04
                raw[:, :, 16:] = data['previous_target'][:, :, 16:] + action[:, :, 16:] * .025
                target = np.clip(raw, lower, upper)
                error = target - data['target_clipped']
                for split, start, end in [('old_heldout32', 0, 32), ('new_heldout8', 32, 40)]:
                    active = data['active_before'][:, start:end].astype(bool)
                    e = error[:, start:end][active]
                    a = action[:, start:end][active]
                    label = data['executed_action'][:, start:end][active]
                    bounds = raw[:, start:end][active]
                    row = dict(model=name, source=source, seconds=seconds, split=split,
                        trajectories=end-start, active_samples=int(active.sum()),
                        executed_action_mse=float(np.square(a-label).mean()),
                        target_range_mean=float((np.abs(e)/(upper-lower)).mean()),
                        target_mae_rad=float(np.abs(e).mean()), thumb_target_mae_rad=float(np.abs(e[:, 16:]).mean()),
                        support_target_mae_rad=float(np.abs(e[:, :16]).mean()),
                        predicted_target_limit_fraction=float(((bounds <= lower) | (bounds >= upper)).mean()),
                        predicted_action_saturation=float((np.abs(a) >= .999999).mean()),
                        checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
                    rows.append(row)
                args.output.write_text(json.dumps(dict(rows=rows, complete=False), indent=2)+'\n')
    args.output.write_text(json.dumps(dict(rows=rows, complete=True,
        scope='CPU replay on shared heldout recorded histories; old32/new8 separated. Own learner RNN starts at zero and follows recorded observations with actual behavior-action history. CPU/GPU numerical differences exist; this is comparative diagnostic, not exact GPU replay or closed-loop success.'), indent=2)+'\n')
    print(json.dumps(dict(complete=True, rows=len(rows))))


if __name__ == '__main__':
    main()
