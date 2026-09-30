"""Freeze reproducible development selection and fixed-budget endpoints once.

This reads development evidence and file hashes only. It never runs evaluation.
The launcher subsequently requires the exact freeze file to be committed.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

from scripts.record_wuji_recovery import D, R, record


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank(row):
    epoch = int(re.findall(r'\d+', row['model'])[-1])
    return (-row['worst_strict'], -row['worst_phase_hold'], -row['worst_body'],
            row['mean_slider_error_m'], epoch, row['model'])


def failure_video(plans, model, development_sha):
    """First failed development row; chosen before final results are opened."""
    for protocol in ['S5', 'S2']:
        for path in plans:
            plan = json.loads(path.read_text())
            if plan['states_sha256'] != development_sha or model not in plan['models']:
                continue
            report_path = path.parent / (model + '-' + protocol) / 'report.json'
            if not report_path.exists():
                continue
            rows = json.loads(report_path.read_text())['records']
            assert len(rows) == 128
            # Prioritize source3, then the first other source with a failure.
            for source in [3, 0, 1, 2]:
                for index in range(source * 32, (source + 1) * 32):
                    if not rows[index]['stable_full_all_endpoints']:
                        selected = [0, 32, 64, 96]
                        selected[source] = index
                        return dict(protocol=protocol, rows=selected, failure_source=source,
                                    failure_row=index, report=str(report_path.relative_to(R)),
                                    report_sha256=sha(report_path),
                                    selection='First strict failure row, source3 first then0/1/2; S5 first thenS2. Fixed before final evaluation. Local resimulation may differ.')
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gates', type=Path, nargs='+', required=True)
    parser.add_argument('--endpoints', nargs='+', required=True)
    parser.add_argument('--anchors', nargs='*', default=['bc100', 'rl1000'])
    parser.add_argument('--replicates', nargs='*', default=[],
                        help='Fixed second-seed endpoints, included without competing for primary checkpoint choice')
    parser.add_argument('--reason', required=True,
                        help='Evidence or actual budget reason for ending development')
    args = parser.parse_args()
    target = D / 'final-freeze.json'
    assert not target.exists(), 'The final freeze is once-only'
    subprocess.run(['python3', '-m', 'scripts.status_wuji_recovery'], cwd=R,
                   check=True, stdout=subprocess.DEVNULL)
    state = json.loads((D / 'STATE.json').read_text())
    assert not state['active_jobs'], 'Finish all development/training jobs first'
    assert not subprocess.check_output(
        ['git', 'status', '--porcelain', '--', 'scripts', 'isaacgymenvs', 'rl_games'],
        cwd=R, text=True).strip(), 'Commit the scientific source first'
    source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R,
                                         text=True).strip()
    candidates = {}
    for path in args.gates:
        for row in json.loads(path.read_text())['models']:
            assert row['cohort_n'] in [32, 64]
            name = row['model']
            if name in candidates:
                assert candidates[name] == row, 'Conflicting checkpoint assessments'
            candidates[name] = row
    families = {}
    for name, row in candidates.items():
        match = re.fullmatch(r'(M|E|Eagg|Ereplay|rl|rlhold|rlclean)(\d+)', name)
        if match:
            families.setdefault(match[1], []).append(row)
    assert set(families) >= {'M', 'E', 'rl', 'rlhold', 'rlclean'}
    selected = {family: min(rows, key=rank)['model'] for family, rows in families.items()}
    endpoint_families = {re.fullmatch(r'(M|E|Eagg|Ereplay|rl|rlhold|rlclean)(\d+)', n)[1]
                         for n in args.endpoints}
    assert endpoint_families == set(families), 'Keep each trained family endpoint'
    assert 'rl4000' in candidates, 'The preregistered four-segment baseline is required'
    # Resolve names through actual development batch plans, never inferred filenames.
    catalog = {}
    plans = sorted((R / 'runs/artmanip-recovery-20260930').glob('*/plan.json'))
    for path in plans:
        plan = json.loads(path.read_text())
        for name, item in plan.get('models', {}).items():
            if name in catalog:
                assert catalog[name] == item, 'Reused model name with different weight'
            catalog[name] = item
    assert not set(args.replicates) & set(selected.values()), 'Replications must not compete in primary family selection'
    names = list(dict.fromkeys([*selected.values(), *args.endpoints,
                              *args.anchors, *args.replicates, 'historical', 'source3']))
    models = {}
    for name in names:
        if name not in ['historical', 'source3']:
            assert name in candidates, 'Every frozen candidate needs full development evidence'
        item = catalog[name]
        assert sha(R / item['path']) == item['sha256']
        models[name] = dict(**item, interface='full_incremental' if name.startswith('rl')
                            else 'mixed_support_initial_thumb_increment',
                            selected_for=[f for f, n in selected.items() if n == name],
                            fixed_endpoint=name in args.endpoints or name in args.replicates,
                            replication_endpoint=name in args.replicates,
                            anchor=name in args.anchors)
    manifest = json.loads((D / 'data/manifest.json').read_text())
    final_states = next(x for x in manifest['entries']
                        if x['split'] == 'final' and x['source'] == 'all')
    assert sha(R / final_states['path']) == final_states['sha256']
    assert final_states['n'] == 512
    # Any prior completed final batch is a protocol violation, not a new freeze.
    assert not any(json.loads(p.read_text()).get('states_sha256') == final_states['sha256']
                   for p in plans)
    ranked = sorted((candidates[n] for n in selected.values()), key=rank)
    development_sha = sha(D/'data/development-all.npy')
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  source_sha=source_sha, models=models, selected_by_family=selected,
                  overall_candidate=ranked[0]['model'], endpoints=args.endpoints,
                  anchors=args.anchors, ranking=ranked,
                  replicates=args.replicates,
                  all_development_candidates=sorted(candidates.values(), key=rank),
                  evidence=[dict(path=str(p), sha256=sha(p)) for p in args.gates],
                  selection='Worst S strict, worst phase hold, worst body, common mean slider error, earlier epoch.',
                  final_states=dict(final_states, per_source=128, previously_evaluated=False),
                  protocols=['S2', 'S5', 'F'], seed=2026093031,
                  S='Separate20s, fixed2/5s, all last9samples perstage error<2mm, full valid/alive, drift<10mm, rotation<.25rad',
                  F='Separate40s, error<10mm continuously45steps before switching; >=1 full open-close cycle. Report full body/alive separately.',
                  final_reselection_allowed=False, no_further_training=True,
                  development_stop_reason=args.reason,
                  video=dict(states='research/artmanip-recovery-20260930/data/development-all.npy',
                             states_sha256=development_sha,
                             rows=[0, 32, 64, 96], model=ranked[0]['model'],
                             failure_example=failure_video(plans, ranked[0]['model'], development_sha),
                             scope='Separate fixed development simulation, not final statistics'),
                  resource_receipt_utc=state['last_resource_check_utc'],
                  occupied_gpu_hours=state['gpu_hours'])
    with target.open('x') as f:
        f.write(json.dumps(result, indent=2) + '\n')
    record('development_ended_final_models_and_protocol_frozen',
           freeze=str(target.relative_to(R)), freeze_sha256=sha(target),
           selected_by_family=selected, overall_candidate=result['overall_candidate'],
           reason=args.reason, next='Commit exact freeze, transfer final states, evaluate once; no reselection or tuning')
    print(json.dumps(dict(freeze=str(target), models=names, selected=selected)))


if __name__ == '__main__':
    main()
