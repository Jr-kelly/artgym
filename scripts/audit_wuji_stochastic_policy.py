"""Frozen-policy exploration diagnostic on the existing fixed-clock benchmark."""
import hashlib
import json
import argparse
import math
from pathlib import Path
import sys
from scripts import audit_wuji_timed_commands as audit
from scripts.audit_distillation_runtime import tensor_digest
import torch


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--noise-sigma-factor', type=float, default=1.0)
    options, remaining = parser.parse_known_args()
    assert 0 < options.noise_sigma_factor <= 1
    sys.argv = [sys.argv[0]]+remaining
    original_make = audit.make_player
    original_loop = audit.run_grasp_evaluation_loop
    checks = dict(active_transitions=0, sampled_actions_differ=0,
                  action_abs_deviation_sum=0.0, thumb_abs_deviation_sum=0.0)
    checks['noise_sigma_factor'] = options.noise_sigma_factor
    references = []

    def make_player(*args, **kwargs):
        env, player = original_make(*args, **kwargs)
        before = {k:v.clone() for k,v in player.model.state_dict().items()}
        sigma = player.model.a2c_network.sigma
        assert isinstance(sigma, torch.nn.Parameter) and tuple(sigma.shape) == (5, 20)
        checks['original_sigma_sha256'] = tensor_digest({'sigma': sigma})
        if options.noise_sigma_factor != 1:
            with torch.no_grad():
                sigma.add_(math.log(options.noise_sigma_factor))
        for name, value in player.model.state_dict().items():
            if name != 'a2c_network.sigma':
                assert torch.equal(before[name], value), name
        checks['sampled_sigma_sha256'] = tensor_digest({'sigma': sigma})
        checks['only_logstd_adjusted_before_rollout'] = True
        original_action = player.get_action

        def sampled(obs, is_deterministic=False, **kw):
            assert not is_deterministic
            incoming = [v.clone() for v in player.states]
            action = original_action(obs, is_deterministic=False, **kw)
            outgoing = player.states
            with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
                player.states = incoming
                mean_action = original_action(obs, is_deterministic=True, **kw)
                assert all(torch.equal(a, b) for a, b in zip(outgoing, player.states))
            player.states = outgoing
            valid = env.eval_active_mask
            delta = (action-mean_action).abs()[valid]
            checks['active_transitions'] += int(valid.sum())
            checks['sampled_actions_differ'] += int((delta > 0).any(-1).sum())
            checks['action_abs_deviation_sum'] += float(delta.sum())
            checks['thumb_abs_deviation_sum'] += float(delta[:, 16:20].sum())
            return action

        player.get_action = sampled
        references.append(player)
        return env, player

    def run_loop(player, env, **kwargs):
        # The student artifact has been installed by this point.
        checks['model_before'] = tensor_digest(player.model.state_dict())
        kwargs['deterministic'] = False
        result = original_loop(player, env, **kwargs)
        checks['model_after'] = tensor_digest(player.model.state_dict())
        assert checks['model_before'] == checks['model_after']
        return result

    audit.make_player = make_player
    audit.run_grasp_evaluation_loop = run_loop
    try:
        audit.main()
        assert checks['active_transitions'] > 0 and checks['sampled_actions_differ'] > 0
        out = Path(sys.argv[sys.argv.index('--output')+1])
        path = out/'report.json'
        report = json.loads(path.read_text())
        (out/'base_report.json').write_bytes(path.read_bytes())
        source = Path(__file__).read_bytes()
        (out/'stochastic_source.py').write_bytes(source)
        report.update(action_selection='sampled Gaussian actions, frozen exploration block0',
                      deterministic=False, stochastic_checks=checks,
                      runtime_logstd_offset=math.log(options.noise_sigma_factor),
                      stochastic_source_sha256=hashlib.sha256(source).hexdigest(),
                      scope='Existing332developmentstates; frozen-policy noise diagnostic, not learned improvement, independent validation, or full five-blockPPO training. Counterfactual means never enter physics.')
        path.write_text(json.dumps(report, indent=2)+'\n')
    finally:
        audit.make_player = original_make
        audit.run_grasp_evaluation_loop = original_loop


if __name__ == '__main__':
    main()
