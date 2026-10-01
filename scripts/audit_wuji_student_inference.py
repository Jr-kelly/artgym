"""Whole-player privacy invariance on nonconstant frozen histories, CPU only."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration
import torch
from omegaconf import OmegaConf
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from scripts.wuji_student_interface import build_encoder, install_student_player, tensor_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--student', type=Path, required=True)
    parser.add_argument('--teacher', type=Path, required=True)
    parser.add_argument('--probes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    cfg = configuration('wuji_multigrasp', 1, ['hand=wuji_paper_official_actuator',
        'object=knife_wuji_bridge3_20260922', 'rl_device=cpu', 'sim_device=cpu'],
        train='wujiAcquisitionSAPG', seed=2026093031)
    config = preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True))
    player = build_policy_player(cfg, config, args.teacher, _infer_expl_num_blocks(args.teacher), 0)
    artifact = torch.load(args.student, map_location='cpu')
    assert artifact['teacher_sha256'] == hashlib.sha256(args.teacher.read_bytes()).hexdigest()
    frozen = lambda: {k: v for k, v in player.model.state_dict().items() if not k.startswith('a2c_network.priv_encoder.')}
    assert tensor_hash(frozen()) == artifact['frozen_hash']
    network = player.model.a2c_network
    calls = [0]
    def teacher_called(*unused):
        calls[0] += 1
    teacher_hook = network.priv_encoder.register_forward_hook(teacher_called)
    encoder = build_encoder(artifact['kind']).eval()
    encoder.load_state_dict(artifact['student_encoder'])
    network.priv_encoder = encoder
    install_student_player(player)
    probes = torch.load(args.probes, map_location='cpu')
    assert len(probes) >= 10
    count = len(probes[0]['x'])
    assert count % 4 == 0
    ids = torch.cat([torch.arange(s * (count // 4), s * (count // 4) + min(8, count // 4)) for s in range(4)])
    inputs = [probe['x'][ids] for probe in probes]
    assert any(not torch.equal(inputs[0], value) for value in inputs[1:]), 'Require nonconstant history fixtures'
    expected_dim = getattr(encoder, 'input_dim', 2055)
    assert all(x.shape[1] == expected_dim for x in inputs)
    critic_inputs = []
    hook = network.critic_priv_encoder.register_forward_pre_hook(lambda module, x: critic_inputs.append(x[0].detach().clone()))
    executions = []
    for perturb in [False, True]:
        player.states = [torch.zeros_like(state[:, ids, :]) for state in probes[0]['rnn']]
        outputs = []
        for probe, x in zip(probes, inputs):
            obs = probe['obs'][ids].clone()
            if perturb:
                obs[:, 111:137] = torch.linspace(-100, 100, 26)
            network.actor_encoder_obs_override = x
            with torch.no_grad():
                action = player.get_action(obs, is_deterministic=True)
            outputs.append((action.clone(), [state.clone() for state in player.states]))
        executions.append(outputs)
    for clean, changed in zip(*executions):
        assert torch.equal(clean[0], changed[0])
        assert all(torch.equal(a, b) for a, b in zip(clean[1], changed[1]))
    assert calls[0] == 0
    assert all(torch.equal(value, critic_inputs[0]) for value in critic_inputs)
    assert tensor_hash(frozen()) == artifact['frozen_hash']
    teacher_hook.remove()
    hook.remove()
    result = dict(student_sha256=hashlib.sha256(args.student.read_bytes()).hexdigest(),
        probes_sha256=hashlib.sha256(args.probes.read_bytes()).hexdigest(),
        snapshots=len(probes), simultaneous_histories=len(ids), states_per_history=len(player.states),
        action_and_all_rnn_exact_invariance=True, actor_teacher_encoder_calls=calls[0],
        critic_receives_constant_normalized_dummy=True, frozen_hash_unchanged=True,
        scope='CPU full get_action path on frozen nonconstant history snapshots, with recurrent state propagated from zero. No simulator or physical success claim; snapshots are not new independent trials.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
