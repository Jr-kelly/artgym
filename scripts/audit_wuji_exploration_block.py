"""Evaluate one frozen SAPG exploration group, retaining the standard scorer."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common  # Isaac Gym before torch.
import torch
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--exploration-block', type=int, required=True)
    args, remaining = parser.parse_known_args()
    assert 0 <= args.exploration_block < 5
    sys.argv = [sys.argv[0]] + remaining
    original = wuji_goal_common.make_player
    captured = []

    def make_player(cfg, checkpoint):
        env, player = original(cfg, checkpoint)
        assert player.model.a2c_network.sigma.shape == (5, 20)
        assert player.intr_reward_coef_embd.shape == (env.num_envs, 1)
        assert (player.intr_reward_coef_embd == 50).all()
        before = tensor_digest(player.model.state_dict())
        identifier = 50.0 - 12.5 * args.exploration_block
        player.intr_reward_coef_embd.fill_(identifier)
        action = player.get_action
        checks = dict(calls=0, identifier=identifier)

        def checked_action(obs, *positional, **keywords):
            assert (obs[:, -1] == identifier).all()
            checks['calls'] += 1
            return action(obs, *positional, **keywords)

        player.get_action = checked_action
        captured.append((player, before, checks))
        return env, player

    wuji_goal_common.make_player = make_player
    try:
        from scripts.audit_wuji_student_actor import main as evaluate
        evaluate()
    finally:
        wuji_goal_common.make_player = original
    assert len(captured) == 1
    player, before, checks = captured[0]
    after = tensor_digest(player.model.state_dict())
    assert before == after and checks['calls'] > 0
    output = Path(sys.argv[sys.argv.index('--output')+1])
    report_path = output/'report.json'
    report = json.loads(report_path.read_text())
    report['exploration_group_audit'] = dict(block=args.exploration_block,
        model_before=before, model_after=after, parameters_unchanged=True, **checks,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Only constant SAPG identifier differs; deterministic actions, frozen student/actor, standard strict development scorer. Group selection is not new training or independent validation.')
    (output/'exploration_block_source.py').write_bytes(Path(__file__).read_bytes())
    report_path.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
