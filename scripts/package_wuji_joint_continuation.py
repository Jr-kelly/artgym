"""Package every joint-only continuation checkpoint and the rejected loss ablation."""
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
    root=Path(__file__).resolve().parents[1];diag=root/'runs/wuji-goal/diagnostics'
    arms={
        'unweighted':('command-continue-final-rescored-1727.json','command-dagger-incremental-continue-1554-v2'),
        'thumb loss x12':('command-thumbunits-final-rescored-1654.json','command-thumbunits-eval-1627-v2')}
    results={}
    for arm,(audit_name,run_name) in arms.items():
        result=json.loads((diag/audit_name).read_text());assert result['status']=='verified'
        expected=16 if arm=='unweighted' else 12
        assert len(result['rows'])==expected
        for row in result['rows']:
            for name,sha in row['source_sha256'].items():
                assert hashlib.sha256((diag/run_name/row['name']/name).read_bytes()).hexdigest()==sha
        results[arm]=result
    out=diag/'release-joint-continuation-and-thumb-ablation-20260923T1751-v3'
    out.mkdir(exist_ok=False);prefix='wuji-joint-continuation-and-thumb-loss-ablation-20260923'
    (out/(prefix+'-all-results.json')).write_text(json.dumps(results,indent=2)+'\n')
    fig,axes=plt.subplots(2,3,figsize=(13,7.5),layout='constrained')
    for row_axes,seconds in zip(axes,[2,5]):
        for ax,metric,title in zip(row_axes,['joint','body','endpoints'],['All criteria','Body stability','All command endpoints']):
            for arm,color in [('unweighted','tab:blue'),('thumb loss x12','tab:orange')]:
                points=sorted([r for r in results[arm]['rows'] if r['seconds']==seconds],key=lambda r:r['update'])
                ax.plot([r['update'] for r in points],[r[metric]/3 for r in points],marker='o',color=color,label=arm)
            ax.set(title=f'{title}, {seconds}s commands',xlabel='Additional DAgger updates',
                   ylabel='Development success (%)',ylim=(-2,102))
            ax.set_xscale('symlog',linthresh=1)
            ax.set_xticks([0,1,25,100,500,1500],labels=['0','1','25','100','500','1500'])
            ax.set_xlim(-.1,2500)
            ax.tick_params(axis='x',labelsize=8)
            ax.grid(alpha=.25)
    axes[0,0].legend(fontsize=9)
    fig.suptitle('Wuji joint-only DAgger: all checkpoints; three grasps x 100 reused perturbations')
    fig.savefig(out/(prefix+'-curves.png'),dpi=180);fig.savefig(out/(prefix+'-curves.pdf'));plt.close(fig)
    (out/(prefix+'-README.txt')).write_text('''Joint-only DAgger continuation and thumb-loss ablation

The unweighted final additional1500 updates (total2000) achieves217/300 with
2s commands and262/300 with5s commands. Body stability:298/300 and300/300.
The matched additional500 comparison is unweighted203/269 versus thumb-loss
x12 147/234. The loss change is rejected. Learning is not monotonic, and all
28 checkpoint/clock conditions are included, not a selected peak.

All results use OLD development states:three trained grasps x100 perturbations
plus an unchanged fourth grasp x32. The fourth has zero strict successes.
This is not independent generalization or hardware validation. No current
object/contact truth reaches the joint-only student during evaluation.

Both arms resume the same final500 incremental student, Adam state and LR2e-5.
They use1024 environments,16 control steps/update,half fixed teacher labels and
half own-state FIFO labels. Unweighted adds24,576,000 physical transitions;
the thumb-loss arm adds8,192,000. Teacher only labels; the student acts.
The ablation multiplies thumb prediction and label by12 inside SmoothL1,
accounting for .3rad output normalization versus .025rad action scale.
The physics, actor interface and all other training settings are unchanged.

Strict20s evaluation:30Hz control,120Hz physics; every external2s/5s command
must stay within2mm for its last9frames, and body drift must remain below
10mm/.25rad throughout. All5,577,600 evaluation transitions were rescored.
The archive contains training/evaluation,source pins,audits,initial states,
the starting student,teacher and fixed-label dataset. GPU5 evaluation was
reassigned after a lease wait; the original handoff/failures are retained.
Download all parts and the manifest,then run the reassembly script to verify
both each part and the complete ZIP before extraction.
''')
    archive=out/(prefix+'-complete-evidence.zip');added=set();source_records=[]
    run_names=[v[1] for v in arms.values()]+['command-dagger-thumbunits-1617-v1',
        'command-thumbunits-runtime-1617-v1','command-dagger-resume-zero-1543-v1',
        'command-dagger-resume-gradient-1545-v1']
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        def add(path,name):
            assert path.is_file(),path
            if name not in added:z.write(path,name);added.add(name)
        for name in run_names:
            folder=diag/name;assert folder.exists(),folder
            for path in sorted(folder.rglob('*')):
                if path.is_file() and not path.is_symlink():add(path,'runs/'+name+'/'+str(path.relative_to(folder)))
            state_file=folder/'status.json'
            if state_file.exists():
                source=json.loads(state_file.read_text()).get('spec',{}).get('source',{})
                if source:
                    source_records.append(source)
                    for key in ['archive','manifest']:
                        path=root/source[key];assert hashlib.sha256(path.read_bytes()).hexdigest()==source[key+'_sha256']
                        add(path,'source/'+path.name)
        paths=[root/'scripts/summarize_wuji_command_student_final.py',root/'scripts/wuji_timed_command_metrics.py',Path(__file__)]
        paths += [diag/v[0] for v in arms.values()]
        paths += [root/'runs/wuji-goal/bridge3-evaluation-states'/name for name in ['mixed332.npy','manifest.json']]
        paths += [diag/'command-dagger-incremental-1504-v3/training/incremental-update0500.pth',
                  diag/'absolute-target-0048-v2/fitting/data.npz',
                  root/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth']
        for path in paths:add(path,'inputs-and-audits/'+path.name)
    script='reassemble-wuji-joint-continuation-20260923.py'
    shutil.copy2(diag/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/script)
    manifest=split_archive(archive,out/'parts',script)
    paths=[p for p in sorted(out.rglob('*')) if p.is_file() and p!=archive]
    (out/'SHA256SUMS-wuji-joint-continuation-20260923.txt').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),
        evaluation_conditions=28,evaluation_transitions=5577600,source_records=source_records,archive=manifest),indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
