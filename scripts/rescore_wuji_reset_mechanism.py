"""Independently verify every frozen reset counterfactual and its physical trace."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml
from scripts.wuji_timed_command_metrics import score_timed_trace


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    assert not args.output.exists()
    state = json.loads((args.run/'status.json').read_text())
    spec = state['spec']
    source_path = args.root/spec['source']['manifest']
    assert digest(source_path) == spec['source']['manifest_sha256']
    source = json.loads(source_path.read_text())
    actual = {s['name']: s for s in state['stages']}
    results, unavailable = {}, []
    formal_cfg = None
    for stage in spec['stages']:
        name = stage['name']
        observed = actual.get(name, {})
        if observed.get('status') != 'completed' or observed.get('returncode') != 0:
            assert args.allow_partial, (name, observed)
            unavailable.append(name)
            continue
        folder = args.run/name
        options = stage['args']
        report = json.loads((folder/'report.json').read_text())
        cfg = yaml.safe_load((folder/'config.yaml').read_text())
        assert cfg['seed'] == 20261127 and cfg['task']['env']['numEnvs'] == stage['rows']
        formal = name.startswith('formal-')
        if formal:
            physical = {k: cfg[k] for k in ['task', 'object', 'hand']}
            if formal_cfg is None:
                formal_cfg = physical
            assert formal_cfg == physical, name
        checkpoint = options[options.index('--checkpoint')+1]
        initial = options[options.index('--initial-states')+1]
        checkpoint = str(Path(checkpoint).relative_to(spec['root']))
        initial = str(Path(initial).relative_to(spec['root']))
        assert digest(args.root/checkpoint) == report['checkpoint_sha256'] == spec['inputs'][checkpoint]
        assert digest(args.root/initial) == report['initial_states_sha256'] == spec['inputs'][initial]
        assert report['initial_state_rows'] == (list(range(332)) if formal else [0, 100, 200])
        seconds = int(options[options.index('--stage-seconds')+1])
        assert report['protocol']['stage_steps'] == seconds*30 and report['protocol']['hold_steps'] == 9
        assert report['protocol']['goal_tolerance_m'] == .002 and not report['protocol']['arrival_used_for_switching']
        assert digest(folder/'source_metrics.py') == source['scripts/wuji_timed_command_metrics.py']
        assert digest(Path(__file__).with_name('wuji_timed_command_metrics.py')) == source['scripts/wuji_timed_command_metrics.py']
        intervention = None
        if stage['module'] == 'scripts.audit_wuji_reset_mechanism':
            intervention = json.loads((folder/'intervention.json').read_text())
            assert intervention['checkpoint_sha256'] == report['checkpoint_sha256']
            assert digest(folder/'source_intervention.py') == intervention['source_sha256'] == source['scripts/audit_wuji_reset_mechanism.py']
            assert intervention['frozen_tensors_verified_after_physics'] and intervention['input_normalizer_only']
            assert intervention['transitions'] == 600*stage['rows']
            assert intervention['constant_initial_targets'] == ('--constant-initial-targets' in options)
            if '--normalizer-source' in options:
                normalizer = str(Path(options[options.index('--normalizer-source')+1]).relative_to(spec['root']))
                assert digest(args.root/normalizer) == intervention['normalizer_source_sha256'] == spec['inputs'][normalizer]
            else:
                assert intervention['normalizer_source_sha256'] is None
                assert intervention['changed_normalizer_tensors'] == []
        with np.load(folder/'trace.npz') as z:
            trace = {k: z[k] for k in z.files}
        assert trace['active'].shape == (600, stage['rows'])
        rescored = score_timed_trace(trace, seconds*30, 9, 600)
        assert rescored['records'] == report['records'], name
        body_step = trace['active'] & ~trace['fall'] & ~trace['invalid']
        body_step &= np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
        body_step &= (trace['drift'] < .01) & (trace['rotation'] < .25)
        body = body_step.all(axis=0)
        if stage.get('identical_to'):
            with np.load(args.run/stage['identical_to']/'trace.npz') as reference:
                assert set(reference.files) == set(trace)
                assert all(np.array_equal(reference[k], trace[k]) for k in trace)
            assert observed['all_trace_arrays_identical'] and not intervention['changed_normalizer_tensors']
        if intervention and intervention['constant_initial_targets']:
            assert np.count_nonzero(trace['action']) == 0
            assert intervention['maximum_constant_target_error_rad'] < 2e-6
        groups = []
        bounds = [(0, 100), (100, 200), (200, 300), (300, 332)] if formal else [(0, 3)]
        for first, last in bounds:
            records = rescored['records'][first:last]
            groups.append(dict(count=last-first, success=sum(r['stable_full_all_endpoints'] for r in records),
                               body=int(body[first:last].sum()), body_stable_half_second=int(body_step[:15, first:last].all(0).sum()),
                               body_stable_two_seconds=int(body_step[:60, first:last].all(0).sum())))
        results[name] = dict(groups=groups, checkpoint_sha256=report['checkpoint_sha256'],
                             trace_sha256=digest(folder/'trace.npz'), intervention=intervention,
                             records=rescored['records'], body=body.tolist(), formal=formal)
    assert results
    result = dict(status='verified_partial' if unavailable else 'verified_complete', results=results,
                  unavailable=unavailable, completed=len(results), expected=len(spec['stages']),
                  physics_transitions=sum((332 if r['formal'] else 3)*600 for r in results.values()),
                  source_sha256=digest(Path(__file__)),
                  scope='Matched H100 frozen mechanism diagnosis, all observed development rows. '
                        'Swapped normalizers and constant-target hold are counterfactual controllers, not new learned policies. '
                        'No independent or hardware result, no selection from these rows claimed.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], completed=result['completed'], physics_transitions=result['physics_transitions'])))


if __name__ == '__main__':
    main()
