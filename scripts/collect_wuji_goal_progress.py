"""Read shared monitor records without confusing the two hosts' PID namespaces."""
import datetime
import json
import re
from pathlib import Path


def read_tail(path):
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size-131072))
        return stream.read().decode(errors='replace')


def main():
    root = Path(__file__).resolve().parents[1]
    utc = datetime.datetime.now(datetime.timezone.utc)
    cst = utc.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
    result = dict(checked_utc=utc.isoformat(), monitors={}, runs={}, utilization={},
                  note='PID liveness comes from each owning host monitor; this collector does not probe cross-host PIDs.')
    monitors = [root/'runs/checkpoint-monitor/status.json']
    monitors += sorted((root/'runs/wuji-goal').glob('*monitor*/status.json'))
    for path in monitors:
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        result['monitors'][str(path.relative_to(root))] = {k:d.get(k) for k in ['heartbeat', 'errors', 'interval_seconds']}
        for name, state in d.get('runs', {}).items():
            result['runs'][name] = {k:state.get(k) for k in ['epoch', 'max_epochs', 'pipeline_status',
                'teacher_pid', 'teacher_alive', 'stalled', 'latest_evaluation', 'best_quality_evaluation',
                'evaluating_epochs', 'queued_epochs', 'failed_epochs']}
            record = result['runs'][name]
            record['monitor_reported_epoch'] = record['epoch']
            log = root/'runs'/name/'teacher.log'
            if log.exists():
                epochs = re.findall(r'epoch\s*:\s*([\d,]+)\s*/\s*([\d,]+)', read_tail(log))
                if epochs:
                    record['epoch'], record['max_epochs'] = [int(x.replace(',', '')) for x in epochs[-1]]
            pipeline = root/'runs'/name/'pipeline-status.json'
            if pipeline.exists():
                record['pipeline_status'] = json.loads(pipeline.read_text()).get('status')
    for path in sorted((root/'runs').glob('gpu-utilization*/status.json')):
        d = json.loads(path.read_text())
        result['utilization'][path.parent.name] = {k:d.get(k) for k in ['heartbeat', 'windows', 'alert', 'current']}
    result['students'] = {}
    for name in sorted(path.name for path in (root/'runs').glob('wuji_student_*') if path.is_dir()):
        path = root/'runs'/name/'pipeline-status.json'
        if path.exists():
            d = json.loads(path.read_text())
            record = {k:d.get(k) for k in ['status', 'started', 'finished', 'teacher_sha256', 'budget_updates', 'source_student']}
            log = path.parent/'distillation.log'
            if log.exists():
                updates = re.findall(r'update=(\d+)', read_tail(log))
                record['updates_observed'] = int(updates[-1])+1 if updates else 0
            result['students'][name] = record
    path = root/'runs/wuji-goal'/('progress-'+cst.strftime('%Y%m%d-%H%M%S')+'.json')
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(path)
    for name, d in result['runs'].items():
        if d.get('pipeline_status') in ['stopped_reallocated', 'failed', 'stopped_posture_gate']:
            continue
        e = d.get('latest_evaluation') or {}
        p = e.get('pose_quality') or {}
        print(json.dumps(dict(name=name, epoch=d.get('epoch'), max_epochs=d.get('max_epochs'),
            evaluated_cp=e.get('epoch'), complete=e.get('successful_trials'), total=e.get('total_trials'),
            strict=p.get('strict_first_cycle_trials'), full=p.get('stable_full_rollout_trials'))))
    for name, d in result['utilization'].items():
        print(name, json.dumps(dict(windows=d['windows'], alert=d['alert'])))


if __name__ == '__main__':
    main()
