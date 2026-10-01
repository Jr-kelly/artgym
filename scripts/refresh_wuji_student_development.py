"""Collect saved paired checkpoints and refresh development evidence, never select models."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_student_goal import D, R, record
from scripts.wuji_student_jobs import REMOTE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--step', type=int, required=True)
    args = parser.parse_args()
    models = [method + '-real-' + str(args.step) for method in ['SC', 'SA']]
    # Require completed physical evaluations AND the independent collector's reports.
    for model in models:
        job = R / 'runs/unified-student-20261001/jobs' / (model + '-development')
        assert json.loads((job / 'result.json').read_text())['exit_code'] == 0
        report = json.loads((D / (model + '-development-analysis') / 'report.json').read_text())
        assert report['independent_rescore']
        assert len([r for r in report['rows'] if r['model'] == model and r['n'] == 32]) == 12
    record('paired_development_refresh_started', models=models,
           next='Copy immutable saved checkpoints and refresh CPU evidence; no model selection or final access')
    for model in models:
        job = R / 'runs/unified-student-20261001/jobs' / (model + '-development')
        identity = json.loads((job / 'identity.json').read_text())
        entries = [token for token in identity['command'] if token.startswith(model + '=')]
        assert len(entries) == 1
        checkpoint = Path(entries[0].split('=', 1)[1])
        assert not checkpoint.is_absolute() and '..' not in checkpoint.parts
        raw = R / 'runs/unified-student-20261001' / (model + '-development') / (model + '-S2') / 'report.json'
        expected = json.loads(raw.read_text())['unified_student_sha256']
        destination = R / checkpoint
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert hashlib.sha256(destination.read_bytes()).hexdigest() == expected
        for path in [checkpoint, checkpoint.with_suffix('.sha256'), checkpoint.parent / 'learning.jsonl']:
            if path == checkpoint and destination.exists():
                continue
            if path.suffix == '.sha256' and (R / path).exists():
                assert (R / path).read_text().strip() == expected
                continue
            subprocess.run(['/usr/bin/rsync', '-a', '-e',
                '/usr/bin/ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024',
                'wangjiarui@10.13.160.5:' + REMOTE + '/' + str(path), str(R / path)],
                check=True, env=host_tool_environment())
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == expected
        assert destination.with_suffix('.sha256').read_text().strip() == expected
    commands = [
        ['scripts.compare_wuji_student_trials', '--left', str(D / (models[0] + '-development-analysis') / 'trials.csv'),
         '--left-model', models[0], '--right', str(D / (models[1] + '-development-analysis') / 'trials.csv'),
         '--right-model', models[1], '--output', str(D / ('action-control-paired' + str(args.step) + '.json'))],
        ['scripts.summarize_wuji_student_stages', '--models', *models, '--output', str(D / ('stages' + str(args.step)))],
        ['scripts.summarize_wuji_student_fit'], ['scripts.summarize_wuji_student_failures'],
        ['scripts.rank_wuji_student_development'],
        ['scripts.plot_wuji_student_learning', '--output', str(D / 'figures')],
        ['scripts.plot_wuji_student_sources'], ['scripts.plot_wuji_student_fitting'],
    ]
    for command in commands:
        subprocess.run([sys.executable, '-m', *command], cwd=R, check=True)
    record('paired_development_refresh_completed', models=models,
           evidence=str((D / ('action-control-paired' + str(args.step) + '.json')).relative_to(R)),
           next='Research decision requires joint checkpoint/source fitting, targets, holds, body stability and failure timing; final remains unopened')


if __name__ == '__main__':
    main()
