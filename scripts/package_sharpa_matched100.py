"""Package equal-frame teacher comparison and split-trial grasp selection."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.package_wuji_dagger_final import split_archive


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal';diag=base/'diagnostics'
    result_path=diag/'sharpa-matched3400-final100-rescored-1639-v2.json';data=json.loads(result_path.read_text())
    assert data['all10_cycle_matrices_rescored']
    out=diag/'release-sharpa-matched3400-20260923T1641';out.mkdir(exist_ok=False)
    prefix='sharpa-equal-frames-cp3400-reward-and-grasp-selection-20260923'
    shutil.copy2(result_path,out/(prefix+'-results.json'))
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for offset,row,color in [(-.18,data['rows'][0],'tab:blue'),(.18,data['rows'][1],'tab:orange')]:
        groups=row['groups']
        axes[0].bar([i+offset for i in range(5)],[100*g['success']/g['total'] for g in groups],width=.36,color=color,label=row['arm'])
        all_success=sum(g['top5_split_trial']['all_grasps_test_success'] for g in groups)
        all_total=sum(g['top5_split_trial']['all_grasps_test_total'] for g in groups)
        rates=[100*all_success/all_total,100*row['top5_split_trial_success']/row['top5_split_trial_total']]
        bars=axes[1].bar([offset,1+offset],rates,width=.36,color=color,label=row['arm'])
        for bar,value in zip(bars,rates):axes[1].text(bar.get_x()+bar.get_width()/2,value+1,f'{value:.2f}%',ha='center',fontsize=9)
    axes[0].set(xticks=range(5),xticklabels=[g['instance'] for g in data['rows'][0]['groups']],
        xlabel='Previously observed held-out geometry',ylabel='Execution success (%)',title='All 287 grasps × 100 randomized trials',ylim=(0,105))
    axes[1].set(xticks=[0,1],xticklabels=['All grasps\n(test trials 50–99)','Selected 5 per geometry\n(test trials 50–99)'],
        title='Selection uses trials 0–49 only',ylabel='Execution success (%)',ylim=(0,109))
    for ax in axes:ax.legend();ax.grid(axis='y',alpha=.25)
    fig.suptitle('Sharpa at 1.088B frames: reward controls and grasp selection')
    fig.savefig(out/(prefix+'-comparison.png'),dpi=180);fig.savefig(out/(prefix+'-comparison.pdf'));plt.close(fig)
    (out/(prefix+'-README.txt')).write_text('''Equal-frame Sharpa teacher comparison, CP3400 /1.088billion training frames

All grasps:upstream15764/28700=54.93%;corrected15475/28700=53.92%.
Corrected minus upstream:-1.01percentage points. Paired grasp bootstrap95%
interval, stratified by the five observed geometries:[-4.75,+2.78]points.
This is not an interval across training seeds or new geometries and does not
establish a stable reward-fix benefit. All10 cycle matrices were rescored.

Grasp-selection diagnostic:select five grasps per geometry using trials0–49,
then score those fixed choices on trials50–99. Upstream1240/1250=99.20%;
corrected1249/1250=99.92%. Source columns and all trial outcomes are provided.
This explains how functional-grasp selection can support reliable demos while
average performance over every candidate remains much lower. These are reused
development geometries/trials, not an untouched blind or real-hardware test.

Success uses10mm arrival-based at-least-one-full-cycle in40s, with randomized
physics. No automatic top5 selection is used in the all-grasp comparison.
Both policies are frozen at equal counters, but have different recovery histories.
This is not the final2billion-frame result and cannot be compared directly with
Wuji's2mm timed20s criterion. Full original checkpoints, evaluation records,
fixed source/assets and independent rescoring program are included in the ZIP.
''')
    run=diag/'sharpa-matched3400-final100-1525-v1'
    source=json.loads((run/'upstream/status.json').read_text())['spec']['source']
    models=base/'frozen-candidates/sharpa-matched3400-20260923'
    archive=out/(prefix+'-complete-evidence.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in sorted(run.rglob('*')):
            if p.is_file():z.write(p,'evaluation/'+str(p.relative_to(run)))
        for row in data['rows']:
            path=models/(row['arm']+'.pth')
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row['checkpoint_sha256']
            z.write(path,'checkpoints/'+path.name)
        for key in ['archive','manifest']:
            p=root/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256']
            z.write(p,'source/'+p.name)
        for p in [result_path,root/'scripts/summarize_sharpa_matched100.py',Path(__file__)]:z.write(p,'source-and-audits/'+p.name)
    script_name='reassemble-sharpa-matched3400-evidence-20260923.py'
    shutil.copy2(diag/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/script_name)
    manifest=split_archive(archive,out/'parts',script_name)
    paths=[p for p in sorted(out.rglob('*')) if p.is_file() and p!=archive]
    (out/'SHA256SUMS-sharpa-matched3400-20260923.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed',archive=manifest),indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
