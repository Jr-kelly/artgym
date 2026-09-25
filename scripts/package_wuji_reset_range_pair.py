"""Package every declared paired continuation CP, including failures and controls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from scripts.package_wuji_dagger_final import split_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--training-spec', type=Path)
    parser.add_argument('--training-audit', type=Path)
    parser.add_argument('--queue', type=Path)
    parser.add_argument('--prefix', default='wuji-reset-range-paired-continuation-20260923')
    parser.add_argument('--description-file', type=Path)
    args = parser.parse_args()
    root, out = args.root, args.output
    goal, diag = root/'runs/wuji-goal', root/'runs/wuji-goal/diagnostics'
    audit = json.loads(args.audit.read_text())
    analysis = json.loads((args.analysis/'analysis.json').read_text())
    assert audit['status'] == analysis['status'] == 'verified_complete'
    assert audit['completed'] == analysis['completed'] == 44
    scorer = Path(__file__).with_name('audit_wuji_reset_range_cp_results.py')
    assert hashlib.sha256(scorer.read_bytes()).hexdigest() == audit['source_sha256']
    training_path = args.training_audit or diag/'reset-range-training-final-audit-20260923-v2.json'
    training = json.loads(training_path.read_text())
    assert training['status'] == 'verified_both_training_complete'
    queue = args.queue or goal/'reset-range-evaluation-20260923-local-v3-queue.json'
    spec_path = args.training_spec or goal/'reset-range-pair-20260923-v2-spec.json'
    spec = json.loads(spec_path.read_text())
    suite_path = root/spec['suite']
    suite = json.loads(suite_path.read_text())['experiments']
    seeds = {int(o.split('=', 1)[1]) for arm in spec['arms']
             for o in suite[arm['name']]['overrides'] if o.startswith('seed=')}
    assert len(seeds) == 1
    training_seed = seeds.pop()
    jobs = json.loads(queue.read_text())
    assert set(j['name'] for j in jobs) == set(audit['results'])
    out.mkdir(exist_ok=False)
    prefix = args.prefix
    for extension in ['png', 'pdf']:
        shutil.copyfile(args.analysis/('checkpoint-curves.'+extension), out/(prefix+'-all44-cp-curves.'+extension))
    shutil.copyfile(args.audit, out/(prefix+'-all44-trajectory-audit.json'))
    shutil.copyfile(args.analysis/'counts.csv', out/(prefix+'-all44-counts.csv'))
    shutil.copyfile(training_path, out/(prefix+'-training-budget-audit.json'))
    partial = diag/'reset-range-control-analysis-20260923-v1' if not args.training_spec else None
    # Preserve and label the earlier partial visual instead of silently replacing it.
    if partial:
        shutil.copyfile(partial/'checkpoint-curves.png', out/(prefix+'-earlier-partial13-cp-curves.png'))
    rows = ['Condition | success/300 | stable body/300 | A/B/C | fourth/32',
            '--- | --- | --- | --- | ---']
    for name, result in audit['results'].items():
        rows.append(f"{name} | {result['success']} | {result['body']} | "+
                    '/'.join(str(g['success']) for g in result['groups'][:3])+f" | {result['groups'][3]['success']}")
    text = '''Wuji paired reset-range continuation: complete development comparison

Both arms start from the exact same frozen teacher and input normalizer, a new
Adam optimizer, LR1e-5 and seed20261124. Each runs5120 environments x32 horizon
x100 epochs=16,384,000 physical transitions, plus a fresh3-epoch PPO preflight
and10,000-transition runtime gate. All CP10/25/50/75/100 are retained. Only the
online reset perturbation amplitude differs:1x is +/-0.5mm position per axis,
0.01rad joints and0.5degree rotation-vector components;2x doubles these bounds.
Training uses the original three grasp rows, never the evaluation rows.

All44 evaluations were completed with normal exits, and every trace was
independently rescored. Each uses the same localGPU protocol, batch332, seed
20261125, same real-size knife, actuator settings and physics. There are two
previously observed DEVELOPMENT cohorts (small/wider); each contains100 rows
for each of three trained grasp families, plus32 unchanged fourth-grasp rows.
The fourth group remains in every trace and audit and is reported separately.
This is not unseen-grasp, unseen-object, new independent or hardware validation.
Do not mix these numbers with earlier4x83 or H100 evaluation numbers.

Every trial lasts20s,30Hz control/120Hz physics. External goals change every2s
or5s, independently of arrival. Every endpoint must remain within2mm for the
last9 frames of its stage. Body drift must stay below10mm/.25rad throughout;
the trial must remain valid/alive. Dashed curves show body stability alone.
All declared CPs, including regressions, are shown. The95% line is a working
target, not a changed success threshold. Selection requires a subsequent new
independent cohort. Plots of earlier13 conditions are explicitly labelled.

The analysis reports paired repairs/regressions and descriptive10,000-draw
grasp-stratified bootstrap intervals (unadjusted, single training seed). Control
statistics use only active transitions before the first body-criterion failure;
associations between saturation/tracking and outcome do not establish causation.
Separate frozen normalizer/holding counterfactuals are a different experiment.
Reward logs and aggregate SAPG KL are not task-success or same-policy-KL metrics.

The source pins, raw traces, all11 frozen policies, training logs, runtime gates,
normalizer statistics and exact initial states are included in the split archive.
Physical knife friction/resistance, camera and execution timing still need real
hardware calibration. The RGB runtime remains bound to its original teacher;
these continued teachers have not been silently substituted into that runtime.

'''+ '\n'.join(rows)+'\n'
    text = text.replace('seed20261124', 'seed'+str(training_seed))
    if partial is None:
        text = text.replace('Plots of earlier13 conditions are explicitly labelled.', '')
    if args.description_file:
        text = args.description_file.read_text()+'\n\n'+'\n'.join(rows)+'\n'
    (out/(prefix+'-README.txt')).write_text(text)
    archive = out/(prefix+'-complete-evidence.zip')
    added = set()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        def add(path, name):
            assert path.is_file() and not path.is_symlink(), path
            if name not in added:
                z.write(path, name)
                added.add(name)
        def folder(path, prefix):
            for item in sorted(path.rglob('*')):
                if item.is_file() and not item.is_symlink():
                    add(item, prefix+'/'+str(item.relative_to(path)))
        for job in jobs:
            folder(goal/'verification'/job['name'], 'evaluations/'+job['name'])
            path = root/job['checkpoint']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == audit['results'][job['name']]['checkpoint_sha256']
            add(path, 'inputs/'+job['checkpoint'])
            options = job['args']
            initial = root/options[options.index('--initial-states')+1]
            add(initial, 'inputs/'+str(initial.relative_to(root)))
        for arm in spec['arms']:
            run = root/'runs'/arm['name']
            for filename in ['pipeline-status.json', 'preflight.log', 'teacher.log']:
                add(run/filename, 'training/'+run.name+'/'+filename)
            folder(run/'summaries', 'training/'+run.name+'/summaries')
            gate = root/arm['gate']
            folder(gate, 'training/'+gate.name)
        folder(root/spec['output'], 'training/coordinator')
        folder(args.analysis, 'analysis/final44')
        if partial:
            folder(partial, 'analysis/earlier-partial13')
        add(scorer, 'source/independent-scorer/'+scorer.name)
        metrics = scorer.with_name('wuji_timed_command_metrics.py')
        add(metrics, 'source/independent-scorer/'+metrics.name)
        for key in ['archive', 'manifest']:
            path = root/spec['source'][key]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['source'][key+'_sha256']
            add(path, 'source/'+path.name)
        for path in [queue, spec_path, suite_path, args.audit, training_path,
                     goal/'research/reset-range-paired-continuation-20260923.md',
                     Path(__file__).with_name('audit_wuji_reset_range_training.py'),
                     Path(__file__).with_name('analyze_wuji_reset_range_pair.py'), Path(__file__)]:
            add(path, 'inputs/'+path.name)
        add(out/(prefix+'-README.txt'), 'README.txt')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    helper = 'reassemble-'+prefix+'.py'
    shutil.copyfile(diag/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py', out/helper)
    manifest = split_archive(archive, out/'parts', helper)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p != archive)
    (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed', files=len(added), archive=manifest), indent=2)+'\n')
    print(out)


if __name__ == '__main__':
    main()
