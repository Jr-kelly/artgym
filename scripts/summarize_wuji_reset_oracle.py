"""Independently rescore privileged reset-stress diagnostics against frozen RGB."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_rgb_independent import wilson


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--rgb-run', type=Path, required=True)
    p.add_argument('--rgb-audit', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--teacher-only', action='store_true', help='Require all eight teacher conditions; causal-truth conditions remain separate and pending.')
    args = p.parse_args()
    assert not args.output.exists()
    state = json.loads((args.run/'status.json').read_text())
    if not args.teacher_only:
        assert state['status'] == 'completed'
    spec = state['spec']
    rgb = json.loads(args.rgb_audit.read_text())
    assert rgb['status'] == 'verified_complete'
    assert rgb['initial_states_sha256'] == spec['initial_states']['sha256']
    assert rgb['evaluation_seed'] == spec['evaluation_seed']
    processes = {s['name']: s for s in state['stages']}
    conditions, audits = {}, []
    for stage in spec['stages']:
        name, mode, sec = stage['name'], stage['feedback'], stage['seconds']
        if args.teacher_only and mode != 'teacher':
            continue
        proc = processes[name]
        assert proc['status'] == 'completed' and proc['returncode'] == 0
        folder = args.run/name
        audit = json.loads((folder/'oracle-audit.json').read_text())
        report = json.loads((folder/'report.json').read_text())
        assert audit['status'] == 'passed' and audit['model_unchanged'] and audit['current_truth_actor_input']
        assert report['checkpoint_sha256'] == '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
        assert report['initial_states_sha256'] == spec['initial_states']['sha256']
        assert report['initial_state_rows'] == stage['initial_state_rows']
        part = name.rsplit('part', 1)[1]
        matched = args.rgb_run/f'formal-mixed-{sec}s-part{part}'
        assert yaml.safe_load((folder/'config.yaml').read_text()) == yaml.safe_load((matched/'config.yaml').read_text())
        with np.load(folder/'trace.npz') as z:
            trace = {k: z[k] for k in z.files}
        with np.load(folder/'oracle-input-trace.npz') as z:
            inputs = {k: z[k] for k in z.files}
        with np.load(matched/'rgb-estimation-trace.npz') as z:
            assert np.array_equal(inputs['features'][0], z['features'][0]), 'Different initial actor observations'
        assert np.array_equal(inputs['active'], trace['active'])
        if mode == 'teacher':
            assert np.array_equal(inputs['actor_privileged'], inputs['true_privileged'])
        assert trace['active'].shape == (600, 83)
        assert audit['checks']['physics_transitions'] == 600*83
        rescore = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
        assert rescore['records'] == report['records']
        body_ok = (trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
                   & np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
                   & (trace['drift'] < .01) & (trace['rotation'] < .25))
        condition = conditions.setdefault(f'{mode}-{sec}s', dict(records={}, groups=[]))
        for local, index in enumerate(stage['initial_state_rows']):
            record = dict(rescore['records'][local], body_only=bool(body_ok[:, local].all()))
            failed_at = np.flatnonzero(~body_ok[:, local])
            record['body_first_failure_s'] = float(failed_at[0]/30) if len(failed_at) else None
            assert str(index) not in condition['records']
            condition['records'][str(index)] = record
        audits.append(dict(stage=name, normal_exit=True, same_config_and_initial_observation=True,
                           hashes={n: hashlib.sha256((folder/n).read_bytes()).hexdigest()
                                   for n in ['report.json', 'trace.npz', 'oracle-input-trace.npz', 'oracle-audit.json']}))
    for key, condition in conditions.items():
        records = condition['records']
        assert set(records) == set(map(str, range(332)))
        sec = key.rsplit('-', 1)[1]
        reference = rgb['conditions']['mixed-'+sec]['records']
        for start, end in [(0, 100), (100, 200), (200, 300), (300, 332)]:
            selected = [records[str(i)] for i in range(start, end)]
            condition['groups'].append(dict(count=len(selected), success=sum(x['stable_full_all_endpoints'] for x in selected),
                                            body=sum(x['body_only'] for x in selected), endpoints=sum(x['all_endpoints_held'] for x in selected)))
        success = np.array([records[str(i)]['stable_full_all_endpoints'] for i in range(300)])
        baseline = np.array([reference[str(i)]['stable_full_all_endpoints'] for i in range(300)])
        condition.update(success=int(success.sum()), trials=300, wilson95=wilson(int(success.sum()), 300),
                         paired_rgb=dict(both_success=int((success & baseline).sum()),
                                         oracle_only=int((success & ~baseline).sum()),
                                         rgb_only=int((~success & baseline).sum()), both_fail=int((~success & ~baseline).sum())))
    assert len(audits) == (8 if args.teacher_only else 16) and len(conditions) == (2 if args.teacher_only else 4)
    result = dict(status='verified_teacher_complete' if args.teacher_only else 'verified_complete', conditions=conditions, audits=audits, physics_transitions=len(audits)*600*83,
                  initial_states_sha256=spec['initial_states']['sha256'], source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  rgb_audit_sha256=hashlib.sha256(args.rgb_audit.read_bytes()).hexdigest(),
                  scope=spec['scope'], independent_validation=False, hardware_validation=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: {f: c[f] for f in ['success', 'trials', 'groups', 'paired_rgb']} for k, c in conditions.items()}))


if __name__ == '__main__':
    main()
