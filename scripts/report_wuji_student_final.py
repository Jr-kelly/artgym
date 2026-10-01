"""Publish tables from the frozen, independently rescored final cohort only."""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

from scripts.summarize_wuji_unified import wilson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.analysis / 'report.json').read_text())
    freeze = json.loads(args.freeze.read_text())
    audit = json.loads(args.audit.read_text())
    assert audit['passed'] and audit['freeze_sha256'] == hashlib.sha256(args.freeze.read_bytes()).hexdigest()
    with (args.analysis / 'trials.csv').open() as stream:
        trials = list(csv.DictReader(stream))
    primary = next(m for m in freeze['models'] if m['role'] == 'primary')
    rows = report['rows']
    ss = [r for r in rows if r['model'] == primary['name'] and r['protocol'] != 'F']
    worst = min(ss, key=lambda r: r['rate'])
    passed = report['gates'][primary['name']]['passed']
    teacher_boundaries = [r for r in rows if r['model'] == freeze['teacher']['name'] and
        (r['rate'] < .8 or (r['protocol'] != 'F' and r['body_rate'] < .95))]
    lines = ['# Frozen unified-student evaluation', '',
        f"Primary **{primary['name']}** {'passes' if passed else 'does not pass'} the preregistered full gate. "
        f"Worst S strict cell: **source {worst['source']} {worst['protocol']}, {worst['success']}/{worst['n']} "
        f"({100 * worst['rate']:.1f}%)**. This is a simulation result under calibrated initial geometry/pose; no hardware validation is claimed.", '',
        'All models were fixed before opening the new final cohort. Each source has 128 episodes per protocol; '
        'protocols share initial states. No teacher failures are removed. Intervals are Wilson 95% intervals, '
        'while gates use observed proportions. Stage holds and repeated checkpoints do not enlarge the denominator.', '',
        '| Model | Protocol | Source | Strict / cycle success (95% CI) | Full-horizon body stability (95% CI) |',
        '|---|---|---:|---|---|']
    enriched = []
    for r in rows:
        cell = [t for t in trials if (t['model'], t['protocol'], int(t['source'])) == (r['model'], r['protocol'], r['source'])]
        assert len(cell) == r['n'] == 128
        assert sum(t['success'] == 'True' for t in cell) == r['success']
        assert sum(t['body_stable'] == 'True' for t in cell) == r['body_stable']
        strict_ci = wilson(r['success'], r['n'])
        body_ci = wilson(r['body_stable'], r['n'])
        enriched.append(dict(r, body_wilson95=body_ci))
        lines.append(f"| {r['model']} | {r['protocol']} | {r['source']} | {r['success']}/128 "
            f"({100*strict_ci[0]:.1f}–{100*strict_ci[1]:.1f}%) | {r['body_stable']}/128 "
            f"({100*body_ci[0]:.1f}–{100*body_ci[1]:.1f}%) |")
    lines += ['', 'S2/S5 are 20 seconds, with external commands every 2/5 seconds, error <2 mm '
        'for the final nine samples of every stage, and full validity/body stability. Body thresholds are '
        '<10 mm drift and <0.25 rad rotation. F is 40 seconds: at least one complete extension–retraction '
        'cycle is functional success; full-horizon stability is reported separately. The F scheduler uses '
        'true slider arrival to issue external commands, so it is not a sensor-free arrival detector.', '',
        'Teacher cells below an absolute threshold: ' + ('; '.join(
            f"{r['protocol']} source {r['source']}: success {r['success']}/128, body {r['body_stable']}/128"
            for r in teacher_boundaries) if teacher_boundaries else 'none') + '. '
        'These episodes remain in every paired comparison; student absolute requirements are unchanged.', '',
        '## Primary full-gate checks', '',
        '| Protocol | Source | Full cell passes | Teacher minus student success (pp) | Teacher minus student body stability (pp) |',
        '|---|---:|---|---:|---:|']
    for check in report['gates'][primary['name']]['checks']:
        lines.append(f"| {check['protocol']} | {check['source']} | {check['passed']} | "
            f"{100*check['strict_drop']:.2f} | {100*check['body_drop']:.2f} |")
    lines += ['', 'S requires success ≥80%, body stability ≥95%, and paired losses ≤10/3 percentage points. '
        'F requires cycle success ≥80%; its body difference is descriptive. A negative difference favors the student.', '',
        '## Paired teacher/student transitions', '',
        '| Student | Protocol | Source | Both pass | Teacher only | Student only | Both fail |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in report['paired_transitions']:
        lines.append('| ' + ' | '.join(str(r[k]) for k in ['model', 'protocol', 'source', 'both_pass', 'teacher_only', 'student_only', 'both_fail']) + ' |')
    lines += ['', 'The underlying JSON also includes paired body-stability transitions and the three '
        'base-configuration clusters (nearby sources 0/1 pooled, source 2, source 3). These clusters are '
        'descriptive summaries, not new grasp or object types.', '', '## Primary failure decomposition', '',
        '| Protocol | Source | Strict successes | Stable body but missed endpoint | Body failure | Opening / closing misses among stable episodes |',
        '|---|---:|---:|---:|---:|---|']
    failures = []
    for r in ss:
        group = [t for t in trials if t['model'] == primary['name'] and t['protocol'] == r['protocol'] and int(t['source']) == r['source']]
        stable = [t for t in group if t['body_stable'] == 'True']
        miss = sum('0' in t['endpoint_holds'] for t in stable)
        body_failed = len(group) - len(stable)
        assert r['success'] + miss + body_failed == 128
        opening = sum('0' in t['endpoint_holds'][::2] for t in stable)
        closing = sum('0' in t['endpoint_holds'][1::2] for t in stable)
        stage_count = 10 if r['protocol'] == 'S2' else 4
        stage_holds = [sum(t['endpoint_holds'][stage] == '1' for t in group) for stage in range(stage_count)]
        first_missed_stages = [t['endpoint_holds'].index('0') + 1 for t in stable if '0' in t['endpoint_holds']]
        body_breach_times = [float(t['first_body_breach_sec']) for t in group if t['body_stable'] != 'True']
        failures.append(dict(protocol=r['protocol'], source=r['source'], strict=r['success'], stable_endpoint_miss=miss, body_failure=body_failed, stable_opening_miss=opening, stable_closing_miss=closing,
            stage_holds=stage_holds, stage_denominator=128,
            median_first_missed_stage_among_stable_failures=statistics.median(first_missed_stages) if first_missed_stages else None,
            median_first_body_breach_seconds_among_body_failures=statistics.median(body_breach_times) if body_breach_times else None))
        lines.append(f"| {r['protocol']} | {r['source']} | {r['success']} | {miss} | {body_failed} | {opening} / {closing} |")
    lines += ['', 'Opening and closing misses can overlap. This partition describes failure location, '
        'not causality. The final cohort is closed after this assessment and must not be used for further tuning.', '',
        '| Protocol | Source | Holds by stage, each /128 | Median first missed stage, stable failures | Median body breach time, body failures |',
        '|---|---:|---|---:|---:|']
    for failure in failures:
        lines.append(f"| {failure['protocol']} | {failure['source']} | {','.join(map(str, failure['stage_holds']))} | "
            f"{failure['median_first_missed_stage_among_stable_failures']} | {failure['median_first_body_breach_seconds_among_body_failures']} |")
    lines += ['', 'Stages are numbered from one, alternating opening and closing. These are repeated measurements '
        'within the same 128 episodes. Missing medians mean no corresponding failures.', '',
        '## Frozen artifacts', '', f"Code SHA256: `{freeze['code_sha256']}`.", '',
        f"Cohort SHA256: `{freeze['cohort']['sha256']}`.", '',
        '| Role | Model | Checkpoint SHA256 |', '|---|---|---|']
    for model in [freeze['teacher']] + freeze['models']:
        lines.append(f"| {model.get('role', 'teacher')} | {model['name']} | `{model['sha256']}` |")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'FINAL_REPORT.md').write_text('\n'.join(lines) + '\n')
    summary = dict(primary=primary, full_gate_pass=passed, worst_S_cell=worst, rows=enriched,
        primary_failures=failures, teacher_absolute_boundary_cells=teacher_boundaries,
        gates=report['gates'], paired_transitions=report['paired_transitions'], clusters=report['clusters'],
        freeze_sha256=audit['freeze_sha256'], provenance_audit=str(args.audit),
        scope='Once-opened frozen final cohort; no model reselection, no hardware claim')
    (args.output / 'final-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(primary=primary['name'], full_gate_pass=passed, worst_S_cell=worst)))


if __name__ == '__main__':
    main()
