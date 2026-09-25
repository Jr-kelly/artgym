"""Rescore every completed paired reset-range checkpoint on the two development cohorts."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--queue', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-partial', action='store_true')
    p.add_argument('--protocol-label', default='local GPU, batch332')
    args = p.parse_args()
    assert not args.output.exists()
    jobs = json.loads(args.queue.read_text())
    results, unavailable = {}, {}
    for job in jobs:
        folder = args.root/'runs/wuji-goal/verification'/job['name']
        status = json.loads((folder/'status.json').read_text()) if (folder/'status.json').exists() else {}
        if status.get('status') != 'completed' or status.get('returncode') != 0:
            assert args.allow_partial, (job['name'], status)
            unavailable[job['name']] = {k: status.get(k) for k in ['status', 'returncode', 'error']}
            continue
        options = job['args']
        initial = args.root/options[options.index('--initial-states')+1]
        seconds = int(options[options.index('--stage-seconds')+1])
        seed = int(options[options.index('--seed')+1])
        checkpoint = args.root/job['checkpoint']
        report = json.loads((folder/'report.json').read_text())
        cfg = yaml.safe_load((folder/'config.yaml').read_text())
        assert cfg['seed'] == seed and cfg['task']['env']['numEnvs'] == 332
        assert report['initial_states_sha256'] == hashlib.sha256(initial.read_bytes()).hexdigest()
        assert report['checkpoint_sha256'] == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        assert report['initial_state_rows'] == list(range(332))
        assert report['hand'] == 'wuji_paper_official_actuator' and report['task'] == 'wuji_acquisition_bridge3_hemisphere'
        assert report['object'] == 'knife_wuji_bridge3_20260922' and report['student_sha256'] is None
        assert report['protocol']['stage_seconds'] == seconds and not report['protocol']['arrival_used_for_switching']
        assert report['protocol']['hold_steps'] == 9 and report['protocol']['goal_tolerance_m'] == .002
        assert abs(report['protocol']['control_dt']-1/30) < 1e-7
        assert hashlib.sha256((folder/'source_metrics.py').read_bytes()).hexdigest() == report['scorer_sha256']
        assert hashlib.sha256(Path(__file__).with_name('wuji_timed_command_metrics.py').read_bytes()).hexdigest() == report['scorer_sha256']
        with np.load(folder/'trace.npz') as z:
            trace = {k: z[k] for k in z.files}
        assert trace['active'].shape == (600, 332)
        rescored = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
        assert rescored['records'] == report['records']
        body = np.all(trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
                      & np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
                      & (trace['drift'] < .01) & (trace['rotation'] < .25), axis=0)
        groups = []
        for start, stop in [(0, 100), (100, 200), (200, 300), (300, 332)]:
            records = rescored['records'][start:stop]
            groups.append(dict(count=stop-start, success=sum(r['stable_full_all_endpoints'] for r in records),
                               body=int(body[start:stop].sum()), endpoints=sum(r['all_endpoints_held'] for r in records)))
        results[job['name']] = dict(checkpoint=job['checkpoint'], checkpoint_sha256=report['checkpoint_sha256'],
                                   initial_states_sha256=report['initial_states_sha256'], initial_states=str(initial),
                                   seconds=seconds, seed=seed, groups=groups,
                                   success=sum(g['success'] for g in groups[:3]), denominator=300,
                                   body=sum(g['body'] for g in groups[:3]), normal_exit=True,
                                   trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest())
    assert results, 'No completed condition to audit yet'
    result = dict(status='verified_partial' if unavailable else 'verified_complete', results=results, unavailable=unavailable,
                  completed=len(results), expected=len(jobs), physics_transitions=len(results)*600*332,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope=f'Matched {args.protocol_label} checkpoint selection on two previously observed development cohorts. Frozen baseline and all declared CPs retained. No new independent/hardware claim.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({n: r['success'] for n, r in results.items()}))


if __name__ == '__main__':
    main()
