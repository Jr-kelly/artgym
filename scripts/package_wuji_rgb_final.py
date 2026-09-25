"""Publish frozen RGB/masked evaluation, actual camera video and reproducible evidence."""
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
    result=diag/'rgb-policy-final-rescored-1652-v2.json';data=json.loads(result.read_text())
    assert data['status']=='verified_complete' and data['physics_transitions']==796800
    out=diag/'release-rgb-state-policy-final5000-20260923T1705-v2';out.mkdir(exist_ok=False)
    prefix='wuji-learned-rgb-vs-masked-final5000-20260923'
    shutil.copy2(result,out/(prefix+'-all-results.json'))
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,seconds in zip(axes,[2,5]):
        for offset,arm,color in [(-.18,'rgb','tab:blue'),(.18,'masked','tab:orange')]:
            condition=data['conditions'][f'{arm}-{seconds}s'];groups=condition['groups']
            bars=ax.bar([i+offset for i in range(4)],[100*g['joint']/g['evaluated'] for g in groups],
                width=.36,label=arm,color=color)
            for bar,g in zip(bars,groups):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,
                str(g['joint'])+'/'+str(g['evaluated']),ha='center',fontsize=8)
        ax.set(xticks=range(4),xticklabels=['Source','Functional 16','Functional 15','Fourth grasp'],ylim=(0,111),
            ylabel='All-command and body success (%)',title=f'External command changes every {seconds} seconds')
        ax.grid(axis='y',alpha=.25);ax.legend(loc='upper center',ncol=2,bbox_to_anchor=(.5,-.12))
    fig.suptitle('Frozen learned camera state + frozen actor: reused development states')
    fig.savefig(out/(prefix+'-comparison.png'),dpi=180);fig.savefig(out/(prefix+'-comparison.pdf'));plt.close(fig)
    (out/(prefix+'-README.txt')).write_text('''Frozen learned RGB state estimator and frozen actor: final5000 update comparison

Every condition was completed and independently rescored:16 batches,796800
physical transitions. Three trained grasps each have100 development perturbations.
An unchanged fourth grasp has32 trials and fails in every condition.
RGB:2s commands268/300,5s commands294/300. Masked-image control:105/300,135/300.
No checkpoint selection:both final5000 models trained with identical initial
weights,24000 training images,5000 Adam updates and640000 supervised samples.
All12000 validation images were independently audited; slider RMSE is about
0.363mm RGB versus0.844mm masked. Offline error is not task success.

Strict task criterion:20s at30Hz actions/120Hz physics, all commands must hold
within2mm during their final0.3s; body drift stays below10mm/0.25rad throughout.
Current object/contact truth does not enter the actor. At t0 the initial pose is
known; later RGB predicts position/rotation/slider. Velocity uses causal finite
differences with alpha0.25. The frozen actor receives those estimates plus hand
kinematics. Camera is320x320,FOV45; this is a simulated sensor, not hardware proof.

The no-text MP4 contains actual saved camera frames from three old-state runtime
rollouts. It has599 frames/30fps and no physics replay or synthetic interpolation.
It illustrates the learned controller and is not an independent evaluation.
Full traces,weights,teacher datasets,source pins,failed graphics initialization,
independent audits and initial states accompany the split evidence archive.
New independent initial-state validation and camera/hardware calibration remain.
''')
    video=diag/'wuji-learned-rgb-fast2s-three-initial-grasps-20260923-no-text.mp4'
    for p in [video,video.with_suffix('.json'),video.with_suffix('.contact.png')]:shutil.copy2(p,out/p.name)
    runs=['rgb-policy-pair-chunks-1603-v3','rgb-state-fitting-1537-v2','rgb-state-collection-1518-v1/2',
        'rgb-state-slow90-1526-v2','rgb-policy-pair-1559-v1','rgb-policy-pair-local-1601-v2',
        'rgb-policy-runtime-rgb-1555-v1','rgb-policy-runtime-masked-1558-v1']
    archive=out/(prefix+'-complete-evidence.zip');added=set()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        def add(p,name):
            assert p.is_file()
            if name not in added:z.write(p,name);added.add(name)
        for name in runs:
            folder=diag/name
            for p in sorted(folder.rglob('*')):
                if p.is_file() and not p.is_symlink():add(p,'runs/'+name+'/'+str(p.relative_to(folder)))
        for name in ['rgb-policy-pair-chunks-1603-v3','rgb-state-fitting-1537-v2']:
            source=json.loads((diag/name/'status.json').read_text())['spec']['source']
            for key in ['archive','manifest']:
                p=root/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256']
                add(p,'source/'+p.name)
        files=[result,diag/'rgb-fit-independent-audit-1554-v2.json',
            root/'scripts/audit_wuji_rgb_policy_results.py',root/'scripts/audit_wuji_rgb_fit.py',
            root/'scripts/audit_wuji_rgb_state_data.py',root/'scripts/video_wuji_rgb_collection.py',Path(__file__),
            root/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy',
            root/'runs/wuji-goal/bridge3-evaluation-states/manifest.json',
            root/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',
            root/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/manifest.json']
        actor=files[-2]
        assert hashlib.sha256(actor.read_bytes()).hexdigest()=='4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
        for p in files:add(p,'audits-and-data/'+p.name)
        for p in sorted((diag/'rgb-ownstate-collection-1637-v1/runtime').rglob('*')):
            if p.is_file():add(p,'video-source-runtime/'+str(p.relative_to(diag/'rgb-ownstate-collection-1637-v1/runtime')))
    script='reassemble-wuji-rgb-evidence-20260923.py'
    shutil.copy2(diag/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/script)
    manifest=split_archive(archive,out/'parts',script)
    paths=[p for p in sorted(out.rglob('*')) if p.is_file() and p!=archive]
    (out/'SHA256SUMS-wuji-rgb-final5000-20260923.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths))
    (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),archive=manifest),indent=2)+'\n');print(out)


if __name__=='__main__':main()
