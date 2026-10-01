"""CPU phase-specific counterfactual fitting on existing frozen teacher histories."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration
import torch
from omegaconf import OmegaConf
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.utils.distill_action_loss import frozen_actor_mean
from isaacgymenvs.utils.torch_jit_utils import unscale
from scripts.wuji_student_interface import build_encoder, legal_policy_observation, tensor_hash
from scripts.wuji_executed_target_loss import executed_targets
from scripts.wuji_kinematics import WujiKinematics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--teacher', type=Path, required=True)
    parser.add_argument('--models', nargs='+', required=True, help='name=checkpoint')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    cfg = configuration('wuji_multigrasp', 1, ['hand=wuji_paper_official_actuator',
        'object=knife_wuji_bridge3_20260922', 'rl_device=cpu', 'sim_device=cpu'],
        train='wujiAcquisitionSAPG', seed=2026093031)
    config = preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True))
    player = build_policy_player(cfg, config, args.teacher, _infer_expl_num_blocks(args.teacher), 0)
    player.model.eval()
    frozen = tensor_hash({k: v for k, v in player.model.state_dict().items()
                          if not k.startswith('a2c_network.priv_encoder.')})
    hand = WujiKinematics()
    lower = torch.tensor(hand.lower, dtype=torch.float32)
    upper = torch.tensor(hand.upper, dtype=torch.float32)
    metrics = ['latent_mse', 'raw_mean_mse', 'clipped_action_mse', 'target_mse_rad2']
    rows, provenance = [], []
    calls = [0]
    def teacher_called(*unused):
        calls[0] += 1
    hook = player.model.a2c_network.priv_encoder.register_forward_hook(teacher_called)
    with torch.no_grad():
        for entry in args.models:
            name, checkpoint = entry.split('=', 1)
            path = Path(checkpoint)
            artifact = torch.load(path, map_location='cpu')
            assert artifact['frozen_hash'] == frozen
            assert artifact['teacher_sha256'] == hashlib.sha256(args.teacher.read_bytes()).hexdigest()
            encoder = build_encoder(artifact['kind']).eval()
            encoder.load_state_dict(artifact['student_encoder'])
            assert encoder.input_dim == 2076
            provenance.append(dict(model=name, checkpoint=checkpoint,
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            for protocol, period in [('S2', 60), ('S5', 150)]:
                fixture = Path('runs/unified-student-20261001') / ('teacher-legal-' + protocol) / 'latent-probes.pth'
                for probe in torch.load(fixture, map_location='cpu'):
                    context = torch.cat([unscale(probe['previous'], lower, upper),
                                         probe['obs'][:, 95:96] / .04], dim=1)
                    prediction = encoder(torch.cat([probe['x'], context], dim=1))
                    label = probe['label']
                    obs = legal_policy_observation(probe['obs'])
                    student = frozen_actor_mean(player, obs, prediction, probe['rnn'])
                    teacher = frozen_actor_mean(player, obs, label, probe['rnn'])
                    inputs = (probe['initial'], probe['previous'], lower, upper)
                    errors = torch.stack([(prediction - label).square().mean(1),
                        (student - teacher).square().mean(1),
                        (student.clamp(-1, 1) - teacher.clamp(-1, 1)).square().mean(1),
                        (executed_targets(student, *inputs) - executed_targets(teacher, *inputs)).square().mean(1)], dim=1)
                    assert len(errors) == 128 and torch.isfinite(errors).all()
                    step = probe['step']
                    for source in range(4):
                        values = errors[source * 32:(source + 1) * 32].mean(0).tolist()
                        rows.append(dict(model=name, protocol=protocol, source=source,
                            pre_action_step=step, stage=step // period,
                            phase='open' if step // period % 2 == 0 else 'close',
                            n_initial_states=32, **dict(zip(metrics, values))))
    assert calls[0] == 0
    hook.remove()
    phases = []
    for key in sorted({(r['model'], r['protocol'], r['source'], r['phase']) for r in rows}):
        selected = [r for r in rows if (r['model'], r['protocol'], r['source'], r['phase']) == key]
        phases.append(dict(model=key[0], protocol=key[1], source=key[2], phase=key[3],
            sampled_times=len(selected), n_initial_states=32,
            **{m: sum(r[m] for r in selected) / len(selected) for m in metrics}))
    scope = ('Fixed teacher histories and identical saved incoming teacher RNN for each counterfactual. '
             'CPU arithmetic and exact target roundtrip; not a new physical rollout or an explanation '
             'of the original learner-state trajectory. Original unfiltered probe snapshots retained. '
             'Sampled times and repeated checkpoints are correlated, not additional independent episodes.')
    (args.output / 'report.json').write_text(json.dumps(dict(models=provenance,
        rows=rows, phases=phases, actor_teacher_encoder_calls=calls[0], scope=scope), indent=2) + '\n')
    with (args.output / 'phases.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(phases[0]))
        writer.writeheader()
        writer.writerows(phases)
    print(json.dumps(dict(models=len(provenance), snapshot_source_cells=len(rows), phase_cells=len(phases))))


if __name__ == '__main__':
    main()
