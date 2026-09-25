"""Package the complete matched privileged diagnosis, including unsuccessful states."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.summarize_wuji_rgb_independent import wilson
from scripts.package_wuji_dagger_final import split_archive


def main():
    root = Path(__file__).resolve().parents[1]
    g, d = root/'runs/wuji-goal', root/'runs/wuji-goal/diagnostics'
    run = d/'reset-oracle-wider-2005-v1'
    state = json.loads((run/'status.json').read_text())
    assert state['status'] == 'completed' and all(s['returncode'] == 0 for s in state['stages'])
    audit = json.loads((d/'reset-oracle-all-rescored-20260923-v1.json').read_text())
    rgb = json.loads((d/'rgb-wider-final-rescored-1940-v1.json').read_text())
    assert audit['status'] == 'verified_complete' and audit['physics_transitions'] == 796800
    prefix = 'wuji-wider-reset-teacher-oracle-diagnosis-20260923'
    out = d/'release-reset-oracle-complete-20260923-v1'
    out.mkdir(exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), layout='constrained')
    lines = []
    labels = ['Frozen RGB', 'Teacher\ntrue state', 'True pose\ncausal velocity']
    for sec, ax in zip([2, 5], axes):
        conditions = [rgb['conditions'][f'mixed-{sec}s'], audit['conditions'][f'teacher-{sec}s'],
                      audit['conditions'][f'causal_truth-{sec}s']]
        good, body_fail, endpoint_fail = [], [], []
        for label, condition in zip(labels, conditions):
            records = [condition['records'][str(i)] for i in range(300)]
            success = sum(r['stable_full_all_endpoints'] for r in records)
            body = sum(r['body_only'] for r in records)
            good.append(success)
            body_fail.append(300-body)
            endpoint_fail.append(body-success)
            lines.append(f'{sec}s, {label.replace(chr(10), " ")}: success {success}/300; body failure {300-body}; body stable but endpoint failure {body-success}.')
        for vals, bottom, color, title in [(good, np.zeros(3), 'tab:green', 'All criteria pass'),
                                          (endpoint_fail, np.array(good), 'tab:orange', 'Stable body, endpoint failure'),
                                          (body_fail, np.array(good)+endpoint_fail, 'tab:red', 'Body criterion failure')]:
            ax.bar(range(3), np.array(vals)/3, bottom=np.array(bottom)/3, color=color, label=title, width=.55)
        for i, count in enumerate(good):
            lo, hi = wilson(count, 300)
            ax.errorbar(i, count/3, yerr=[[count/3-lo*100], [hi*100-count/3]], fmt='none', ecolor='black', capsize=3)
            ax.text(i, 103, f'{count}/300', ha='center', fontsize=10)
        ax.set(title=f'{sec}s commands', xticks=range(3), xticklabels=labels, ylim=(0, 111), ylabel='Previously observed trials (%)')
    axes[0].legend(loc='lower left', fontsize=8)
    fig.suptitle('Wider reset diagnosis: same states, frozen actor and physics\nPrivileged arms diagnose limitations; they are not deployable policies')
    fig.savefig(out/(prefix+'-success-and-failures.png'), dpi=180)
    fig.savefig(out/(prefix+'-success-and-failures.pdf'))
    plt.close(fig)
    notes = '\n'.join(lines)+'''

All 16 privileged conditions and 796800 transitions were independently rescored
after normal process exits. All physical configs and initial actor observations
match the earlier frozen RGB run. The exact same 332 initial rows and same seed
were used in four batches of 83 per clock. First 300: three trained grasp families;
the fourth 32 remain failures and remain in every raw trace and audit.

teacher receives unmodified current simulator state. causal_truth receives
exact body/slider pose reconstructed with the same causal velocity estimator
as RGB. Both arms are privileged diagnostics, not deployable student policies.
They construct the same cameras and RGB network as the previous experiment,
preserving RNG consumption, but render only four diagnostic frame times.
The RGB estimator is not used for actions in these two diagnostic arms.

The stress cohort was observed before this diagnosis; it is now development
data. It is not a new independent test. Reset ranges: +/-1mm per position axis,
+/-0.02rad joints and +/-1degree rotation-vector components. Same three grasp
families, same knife/camera/physics. A future independent test must use new rows.

Each trial lasts 20s, at 30Hz control and 120Hz physics. External commands alternate
every 2s or 5s. All stage endpoints require nine frames within 2mm. The knife body
must remain within 10mm and .25rad throughout, and the trial must stay valid/alive.
Body failures and endpoint failures overlap physically; the chart assigns body
failures first, then shows endpoint-only failures among body-stable states.
Black error bars show Wilson95 intervals for joint success. No threshold changed.

Earlier RGB comparison evidence is already on the same GitHub Release as
wuji-rgb-wider-reset-stress300-20260923-complete-evidence.zip.part000 etc.
Complete archive SHA256: 5af23af4e5f7676142a207e272ee45ac1051b0c79185dfd26d37f0b022d74cf9.
Release: https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921
No real hardware validation. Diagnostic images contain no text.
'''
    (out/(prefix+'-README.txt')).write_text(notes)
    shutil.copyfile(d/'reset-oracle-all-rescored-20260923-v1.json', out/(prefix+'-all-trial-audit.json'))
    archive = out/(prefix+'-complete-evidence.zip')
    added = set()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        def add(path, name):
            assert path.is_file(), path
            if name not in added:
                z.write(path, name)
                added.add(name)
        for folder in [run, d/'reset-oracle-finalization-20260923-v1', d/'reset-oracle-finalization-20260923-v2']:
            for path in folder.rglob('*'):
                if path.is_file() and not path.is_symlink():
                    add(path, 'runs/'+folder.name+'/'+str(path.relative_to(folder)))
        for source in [state['spec']['source'], json.loads((d/'reset-oracle-audit-source-20260923-v1.json').read_text())]:
            for key in ['archive', 'manifest']:
                path = root/source[key]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == source[key+'_sha256']
                add(path, 'source/'+path.name)
        for key in ['initial_states', 'artifact']:
            item = state['spec'][key]
            path = root/item['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
            add(path, 'inputs/'+path.name)
        add(g/'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth', 'inputs/teacher.pth')
        for name in ['reset-oracle-all-rescored-20260923-v1.json', 'reset-oracle-teacher-rescored-20260923-v1.json',
                     'reset-oracle-teacher-decomposition-20260923-v1.json', 'rgb-wider-final-rescored-1940-v1.json',
                     'finalize-reset-oracle-20260923-v1.py', 'finalize-reset-oracle-20260923-v2.py']:
            add(d/name, 'inputs/'+name)
        add(Path(__file__), 'inputs/'+Path(__file__).name)
        add(out/(prefix+'-README.txt'), 'README.txt')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    helper = 'reassemble-'+prefix+'.py'
    shutil.copyfile(d/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py', out/helper)
    manifest = split_archive(archive, out/'parts', helper)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p != archive)
    (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed', files=len(added), archive=manifest), indent=2)+'\n')
    print(out)


if __name__ == '__main__':
    main()
