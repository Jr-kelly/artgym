"""Integrate timestamped device samples over actual job intervals."""
import argparse
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def seconds(value):
    return datetime.datetime.fromisoformat(value).timestamp()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    history = ROOT / 'research/multigrasp-20260928/receipts/gpu-history.jsonl'
    samples = []
    for line in history.read_text().splitlines():
        record = json.loads(line)
        utilization = {int(parts[0]): float(parts[1].strip().rstrip('%')) / 100
                       for parts in (line.split(',') for line in record['gpu'].splitlines())}
        samples.append((seconds(record['time']), utilization))
    samples.sort(key=lambda item: item[0])

    def integrate(start, end, gpu=None):
        covered = busy = 0.
        for (left, values), (right, _) in zip(samples, samples[1:]):
            # Do not interpolate across monitor outages longer than two minutes.
            if right - left > 120:
                continue
            duration = max(0., min(end, right) - max(start, left))
            utilization = sum(values.values()) / len(values) if gpu is None else values[gpu]
            covered += duration
            busy += duration * utilization
        return dict(covered_seconds=covered, utilization_weighted_busy_seconds=busy,
                    time_weighted_utilization_pct=100 * busy / covered if covered else None)

    jobs = []
    names = ['mg_' + arm + '_seed2801' for arm in 'ABCD']
    names += [f'expert_row{row}_seed2810' for row in (3, 5, 11)]
    for name in names:
        path = ROOT / 'runs/multigrasp-20260928' / name / 'status.json'
        if not path.exists():
            continue
        state = json.loads(path.read_text())
        if state['status'] != 'completed':
            continue
        start, end = seconds(state['started']), seconds(state['finished'])
        jobs.append(dict(name=name, gpu=state['gpu'], started=state['started'], finished=state['finished'],
                         device_allocation_hours=(end-start)/3600,
                         measured=integrate(start, end, state['gpu'])))
    end = samples[-1][0]
    report = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  last_sample_utc=datetime.datetime.fromtimestamp(end, datetime.timezone.utc).isoformat(),
                  latest_four_hours=integrate(end-14400, end), jobs=jobs,
                  total_completed_training_device_allocation_hours=sum(row['device_allocation_hours'] for row in jobs),
                  scope='One GPU per training. Allocation hours are real job wall time including startup; busy seconds integrate sampled nvidia-smi utilization, not kernel-profiler GPU time or platform accounting. Sampling begins after the first jobs start. No interpolation over gaps >120s. Last4h is whole-machine mean across all4GPUs, including idle devices.')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
