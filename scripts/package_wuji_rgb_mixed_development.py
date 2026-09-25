"""Publish the complete mixed-image development result and added training data."""
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
    names={'Teacher-image data':'rgb-policy-final-rescored-1652-v2.json',
           'Mixed-image data':'rgb-mixed-final-rescored-1802-v1.json'}
    data={key:json.loads((diag/name).read_text()) for key,name in names.items()}
    assert all(v['status']=='verified_complete' and v['physics_transitions']==796800 for v in data.values())
    out=diag/'release-rgb-mixed-development-20260923T1827-v1';out.mkdir(exist_ok=False)
    prefix='wuji-rgb-mixed-data-final5000-development-20260923'
    (out/(prefix+'-all-results.json')).write_text(json.dumps(data,indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(11.5,8),layout='constrained')
    for row,seconds in enumerate([2,5]):
        for column,arm in enumerate(['rgb','masked']):
            ax=axes[row,column]
            for offset,(name,color) in zip([-.18,.18],[('Teacher-image data','tab:blue'),('Mixed-image data','tab:orange')]):
                groups=data[name]['conditions'][f'{arm}-{seconds}s']['groups']
                bars=ax.bar([i+offset for i in range(4)],[100*g['joint']/g['evaluated'] for g in groups],
                            width=.36,label=name,color=color)
                for bar,g in zip(bars,groups):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,
                    f"{g['joint']}/{g['evaluated']}",ha='center',fontsize=8)
            ax.set(xticks=range(4),xticklabels=['Grasp A','Grasp B','Grasp C','Fourth'],ylim=(0,116),
                   ylabel='All-command and body success (%)',title=f'{arm.upper()} input, {seconds}s commands')
            ax.grid(axis='y',alpha=.2)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2)
    fig.suptitle('Frozen estimators + frozen actor: all old development states')
    fig.savefig(out/(prefix+'-comparison.png'),dpi=180);fig.savefig(out/(prefix+'-comparison.pdf'));plt.close(fig)
    prior=json.loads((diag/'release-rgb-state-policy-final5000-20260923T1705-v2/package-status.json').read_text())['archive']
    (out/(prefix+'-prior-teacher-data-dependency.json')).write_text(json.dumps(dict(
        release='https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921',
        archive=prior,reason='Original 36000 teacher images and original fit initialization are already published in this verified archive. New bundle contains all additional own-state images and mixed fitting/evaluation.'),indent=2)+'\n')
    (out/(prefix+'-README.txt')).write_text('''Frozen mixed-image estimator: complete development results

RGB final5000:2s commands290/300;5s commands297/300. Image-masked controls:
135/300 and202/300. Original teacher-image-only RGB:268/294;masked105/135.
All16 mixed conditions and796800 physical transitions are independently
rescored. Three trained grasps each have100 OLD development perturbations.
Grasp A/B/C are source/functional16/functional15. The unchanged fourth grasp
has0/32 strict successes for every model and clock. These are not new-grasp,
independent-reset, new-geometry or hardware claims. The independent frozen
paired cohort is a separate experiment and is not included in these numbers.

Training adds36000 images from the original frozen RGB controller's own
trajectories to36000 teacher images. Same60/30 initial-row train/validation
partition,original initialization and original teacher-training normalization.
There are48000 training and24000 validation images;each batch contains64
teacher-domain and64 own-state samples,5000 Adam updates,LR2e-4,batch128,
640000 sampled examples per RGB/masked arm. Final5000 only,no peak selection.
All fitting chunks,validation predictions and optimizer counters were audited.

Strict20s control:30Hz actions/120Hz physics,2s/5s external commands;each
command's final9frames must remain within2mm,body drift below10mm/.25rad
throughout. At t0 only reset-known geometry is used;then RGB predicts body
translation/rotation and slider position. Velocity is a causal finite
difference with alpha.25. No current object/contact truth reaches the actor.

The added evidence ZIP contains all own-state images,mixed training checkpoints,
all16 traces,runtime gates,source pins,initial states,frozen actor,audits,and
the command-counterfactual diagnostic. The original36000 teacher images and
initialization are a published dependency identified by exact SHA256 in the
dependency manifest,not silently omitted from a claimed standalone bundle.
The counterfactual uses only2400 old validation samples and does not replace
the full24000-sample fit audit or demonstrate task success.
''')
    runs=['rgb-mixed-fitting-1705-v1','rgb-ownstate-collection-1637-v1',
          'rgb-mixed-policy-chunks-1718-v1','rgb-mixed-local-runtime-1718-v1',
          'rgb-goal-counterfactual-1738-v1']
    archive=out/(prefix+'-added-data-and-evidence.zip');added=set()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        def add(path,name):
            assert path.is_file(),path
            if name not in added:z.write(path,name);added.add(name)
        for name in runs:
            folder=diag/name
            for path in sorted(folder.rglob('*')):
                if path.is_file() and not path.is_symlink():add(path,'runs/'+name+'/'+str(path.relative_to(folder)))
            source=json.loads((folder/'status.json').read_text()).get('spec',{}).get('source',{}) if (folder/'status.json').exists() else {}
            if source:
                for key in ['archive','manifest']:
                    path=root/source[key];assert hashlib.sha256(path.read_bytes()).hexdigest()==source[key+'_sha256']
                    add(path,'source/'+path.name)
        files=[diag/name for name in names.values()]+[Path(__file__),root/'scripts/analyze_wuji_rgb_goal_counterfactual.py',
            root/'scripts/audit_wuji_rgb_policy_results.py',root/'scripts/audit_wuji_rgb_mixed_fit.py',
            root/'scripts/audit_wuji_rgb_state_data.py',root/'runs/wuji-goal/rgb-mixed-fit-data-spec-1705-v1.json',
            root/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy',
            root/'runs/wuji-goal/bridge3-evaluation-states/manifest.json',
            root/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth']
        files += [p for p in out.glob('*') if p.is_file() and p!=archive]
        for path in files:add(path,'audits-and-inputs/'+path.name)
    script='reassemble-wuji-rgb-mixed-development-20260923.py'
    shutil.copy2(diag/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/script)
    manifest=split_archive(archive,out/'parts',script)
    paths=[p for p in out.rglob('*') if p.is_file() and p!=archive]
    (out/'SHA256SUMS-wuji-rgb-mixed-development-20260923.txt').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(paths)))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),archive=manifest),indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
