"""Collect completed core-task trials and recompute metrics from physical traces."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from scripts.host_tool_environment import host_tool_environment
from scripts.monitor_wuji_checkpoints import now
from scripts.wuji_arrival_metrics import score_arrival_trace
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v1', 'v2'], default='v2')
    version = parser.parse_args().version
    root = Path(__file__).resolve().parents[1]
    remote = '/home/wangjiarui/artgym-experiments-20260921'
    goal = root/'runs/wuji-goal'
    preparation = json.loads((goal/('diagnostics/core-task-evaluation-preparation-20260924-'+version+'.json')).read_text())
    video_version = 'v5' if version == 'v2' else version
    specs = preparation['specs'] + json.loads((goal/('diagnostics/core-task-video-specs-20260924-'+video_version+'.json')).read_text())
    paths = []
    for filename in specs:
        spec = json.loads((root/filename).read_text())
        paths.append(spec['output'])
        paths.extend(s['output'] for s in spec['stages'])
    legacy_paths = []
    for filename in goal.glob('core-task-*-20260924-v[123]-spec.json'):
        old = json.loads(filename.read_text())
        legacy_paths.extend([old['output']] + [s['output'] for s in old['stages']])
    queried_paths = sorted(set(paths + legacy_paths))
    connection = 'ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10'
    import shlex
    code = ('from pathlib import Path; import json; r=Path('+repr(remote)+'); paths='+repr(queried_paths)+'\n'
            'print(json.dumps({p:json.loads((r/p/"status.json").read_text()) for p in paths if (r/p/"status.json").exists()}))\n')
    env = host_tool_environment()
    raw = subprocess.check_output(shlex.split(connection)+['wangjiarui@10.14.0.106', 'python3 -'],
                                  input=code.encode(), env=env)
    statuses = json.loads(raw)
    completed = [p for p in paths if p.startswith('runs/wuji-goal/verification/') and
                 statuses.get(p, {}).get('status') == 'completed']
    failed = [p for p in queried_paths if statuses.get(p, {}).get('status') == 'failed']
    out = goal/('diagnostics/core-task-collected-20260924-'+version)
    out.mkdir(exist_ok=True)
    listing = out/'sync.txt'
    listing.write_text('\n'.join(p+'/' for p in sorted(set(completed+failed)))+'\n')
    if completed or failed:
        subprocess.run(['rsync', '-azr', '--files-from='+str(listing), '-e', connection,
                        'wangjiarui@10.14.0.106:'+remote+'/', str(root)+'/'], env=env, check=True)
    results = {}
    for path in completed:
        directory = root/path
        report = json.loads((directory/'report.json').read_text())
        trace = np.load(directory/'trace.npz')
        protocol = report['protocol']
        if protocol['arrival_used_for_switching']:
            rescored = score_arrival_trace(trace, round(protocol['total_seconds']/protocol['control_dt']),
                                          protocol['goal_tolerance_m'])
            keys = ['first_cycle', 'three_cycles', 'alive_full', 'strict_body_full']
        else:
            rescored = score_timed_trace(trace, protocol['stage_steps'], 9, 600)
            keys = ['first_cycle', 'all_commands_attained', 'all_endpoints_held',
                    'stable_full_all_endpoints', 'alive_full']
        assert report['records'] == rescored['records'], path
        for key in keys:
            assert report[key] == rescored[key], (path, key)
        entry = dict(trace_sha256=hashlib.sha256((directory/'trace.npz').read_bytes()).hexdigest(),
                     report_sha256=hashlib.sha256((directory/'report.json').read_bytes()).hexdigest(),
                     num_envs=report['num_envs'], protocol=protocol,
                     totals={k: report[k] for k in keys}, groups=[])
        if report['num_envs'] == 300:
            for group in range(3):
                records = report['records'][group*100:(group+1)*100]
                item = dict(group=group, n=100, **{k:sum(row[k] for row in records) for k in keys})
                if protocol['arrival_used_for_switching']:
                    cycles = [row['cycles'] for row in records]
                    item.update(cycles_mean=float(np.mean(cycles)), cycles_min=min(cycles), cycles_max=max(cycles))
                else:
                    valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
                    hit = valid & (np.abs(trace['slider']-trace['goal']) < .01)
                    steps = protocol['stage_steps']
                    holds = np.stack([hit[i+steps-9:i+steps].all(0) for i in range(0, 600, steps)])
                    item['all_endpoints_held_10mm'] = int(holds[:, group*100:(group+1)*100].all(0).sum())
                entry['groups'].append(item)
        results[path] = entry
    summary = dict(time=now(), statuses={p:d['status'] for p,d in statuses.items()},
                   historical_failed_paths=failed,
                   all_queues_completed=all(statuses.get(json.loads((root/f).read_text())['output'], {}).get('status') == 'completed' for f in specs),
                   completed_physics_trials=len(results), results=results)
    (out/'latest.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(dict(time=summary['time'], completed=len(results), all_completed=summary['all_queues_completed'],
                         results={p:dict(totals=d['totals'], groups=d['groups']) for p,d in results.items()})))


if __name__ == '__main__':
    main()
