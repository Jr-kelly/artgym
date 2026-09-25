"""Separate physical slider damping from the teacher's damping observation.

Nine common-state conditions cross actual and observed damping (.3, 3, 30).
Off-diagonal conditions deliberately give incorrect privileged information;
they are causal diagnostics, never deployable policies or calibrated dynamics.
The actor alone controls every physics step. All failures remain in the report.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists()
    source = Path(__file__).read_bytes()
    (args.output/'factorial_source.py').write_bytes(source)
    settings = list(itertools.product([.3, 3., 30.], repeat=2))
    states = np.load(args.initial_states)[:20]
    assert len(states) == 20 and np.isfinite(states).all()
    np.save(args.output/'common_states.npy', np.tile(states, (len(settings), 1)))
    actual_values = np.repeat([a for a, _ in settings], 20)
    observed_values = np.repeat([o for _, o in settings], 20)
    checks = dict(property_checks=0, privileged_input_checks=0, refreshes=0)
    original_make = wuji_goal_common.make_player
    holder = {}

    def make_player(cfg, checkpoint):
        env, player = original_make(cfg, checkpoint)
        assert not env.randomize and env.num_envs == 180
        holder['env'] = env
        for i, value in enumerate(actual_values):
            props = env.gym.get_actor_dof_properties(env.envs[i], env.object_handles[i])
            assert len(props) == 1
            props['damping'][:] = value
            env.gym.set_actor_dof_properties(env.envs[i], env.object_handles[i], props)
        expected = torch.as_tensor(observed_values, device=env.device, dtype=torch.float32)
        refresh_base = env._get_object_props

        def refresh():
            refresh_base()
            env.object_dof_damping[:, 0] = expected
            checks['refreshes'] += 1

        env._get_object_props = refresh
        refresh()
        compute_base = env._compute_sapg_priv_observations

        def compute():
            policy, privileged = compute_base()
            # object pose 7 + moving-link pose 7 + two masses 2 + friction 1.
            assert privileged.shape[1] == 21
            assert torch.allclose(privileged[:, 17], expected)
            checks['privileged_input_checks'] += 1
            return policy, privileged

        env._compute_sapg_priv_observations = compute
        action_base = player.get_action

        def action(*a, **kw):
            if checks['property_checks'] in (0, 599):
                for i, value in enumerate(actual_values):
                    props = env.gym.get_actor_dof_properties(env.envs[i], env.object_handles[i])
                    assert np.isclose(props['damping'][0], value)
            checks['property_checks'] += 1
            return action_base(*a, **kw)

        player.get_action = action
        return env, player

    wuji_goal_common.make_player = make_player
    from scripts import audit_wuji_timed_commands
    argv = sys.argv
    try:
        sys.argv = [argv[0], '--checkpoint', str(args.checkpoint), '--initial-states',
                    str(args.output/'common_states.npy'), '--task', 'wuji_acquisition_official_support40mrad',
                    '--hand', 'wuji_paper_official_actuator', '--stage-seconds', '2', '--seed', '1616',
                    '--output', str(args.output)]
        audit_wuji_timed_commands.main()
    finally:
        sys.argv = argv
        wuji_goal_common.make_player = original_make
    report = json.loads((args.output/'report.json').read_text())
    assert report['num_envs'] == 180 and report['recorded_steps'] == 600
    assert checks['property_checks'] == 600 and checks['privileged_input_checks'] >= 600
    keys = ['first_cycle', 'first_cycle_strict', 'all_commands_attained', 'all_endpoints_held',
            'stable_full', 'stable_full_all_endpoints', 'fall']
    rows = []
    for i, (actual, observed) in enumerate(settings):
        trials = report['records'][20*i:20*(i+1)]
        rows.append(dict(actual_damping_Ns_per_m=actual, observed_damping_Ns_per_m=observed,
                         trials=20, **{k:sum(t[k] for t in trials) for k in keys}))
    result = dict(status='completed', scope=__doc__, results=rows, checks=checks,
                  source_sha256=hashlib.sha256(source).hexdigest(),
                  checkpoint_sha256=report['checkpoint_sha256'],
                  initial_source_sha256=hashlib.sha256(args.initial_states.read_bytes()).hexdigest(),
                  rows_per_condition=list(range(20)),
                  configuration_note='config.yaml holds base values; the actual and observed per-environment overrides are recorded here.')
    (args.output/'factorial_report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
