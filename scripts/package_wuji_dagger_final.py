"""Publishable full DAgger evidence, including every failed condition and model."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def split_archive(path,folder,script_name='reassemble-wuji-evidence-20260923.py'):
    folder.mkdir(exist_ok=False)
    records=[];whole=hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            data=stream.read(64*1024*1024)
            if not data:break
            whole.update(data)
            part=folder/(path.name+f'.part{len(records):03d}')
            part.write_bytes(data)
            records.append(dict(name=part.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    manifest=dict(archive=path.name,bytes=path.stat().st_size,sha256=whole.hexdigest(),parts=records,
        reassembly='python3 '+script_name+' '+path.stem+'-parts-manifest.json; validates each part and complete ZIP')
    (folder/(path.stem+'-parts-manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    diag=ROOT/'runs/wuji-goal/diagnostics'
    out=diag/'release-dagger-final-and-offline-parts-20260923T1557'
    out.mkdir(exist_ok=False)
    prefix='wuji-own-state-dagger-final500-20260923'
    pair=json.loads((diag/'command-dagger-pair-final-audit-1540.json').read_text())
    assert pair['all24_traces_rescored']
    rows=[]
    for arm in ['absolute','incremental']:
        doc=json.loads((diag/f'command-dagger-{arm}-final-rescored-1540.json').read_text())
        assert doc['all12_rescored'];rows+=doc['rows']
    (out/(prefix+'-all-results.json')).write_text(json.dumps(dict(pair=pair,conditions=rows),indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
    for ax,key,title in zip(axes,['joint','body','endpoints'],['All criteria','Body stability','All command endpoints']):
        for arm,color in [('absolute','tab:blue'),('incremental','tab:orange')]:
            for sec,style in [(2,'-'),(5,'--')]:
                points=sorted([v for v in rows if v['arm']==arm and v['seconds']==sec],key=lambda v:v['update'])
                ax.plot([v['update'] for v in points],[v[key]/3 for v in points],style,color=color,marker='o',label=f'{arm}, {sec}s')
        ax.set(title=title,xlabel='Own-state training update',ylabel='Development success (%)',ylim=(-2,102));ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle('Wuji: final budget, all checkpoints; 3 grasps × 100 reused perturbations')
    fig.savefig(out/(prefix+'-curves.png'),dpi=180);fig.savefig(out/(prefix+'-curves.pdf'));plt.close(fig)
    (out/(prefix+'-README.txt')).write_text('''Wuji own-state DAgger, complete final500 comparison

Final absolute:120/300 fast,192/300 slow. Final incremental:169/300 fast,
228/300 slow. Fourth grasp:0/32 for both. All24 checkpoint/clock conditions
independently rescored from4,780,800 recorded physical evaluation transitions.
This is improvement, not reliable independent or hardware success.

Each arm:1024 environments ×16 controlsteps ×500 updates=8,192,000 physical
transitions. Student alone acts; frozen teacher labels its next bounded joint
targets. Half each Adam batch comes from fixed teacher trajectories, half from
the student's FIFO.4000 Adamsteps,4,096,000 sampled labels,LR2e-5,seed20261080.
116→256→128→20 MLP:current joints,previous actions,known initial state and
targets,external command. No current object truth enters student. This differs
from the paper's latent-MSE student. Source and all failed starts are retained.

CP0 is the final offline model, not an untrained model. Absolute peaked at250
and then regressed; every checkpoint is included. Development success requires
each2s/5s command's last9frames within2mm, body translation<10mm and rotation
<.25rad throughout20s, with valid physics.332states are300 perturbations of
three seen grasps plus32 of one fourth grasp, not332different grasps.

ZIP is split into64MiB files for reliable uploading. Download every part and
its manifest and run the provided reassembly script. Failed prior780MB upload
is not counted as published; that original offline ZIP is also supplied in
separate verified parts. No data or failed trials are omitted from either ZIP.
''')
    archive=out/(prefix+'-complete-evidence.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for arm in ['absolute','incremental']:
            run=diag/f'command-dagger-{arm}-1504-v3'
            for f in sorted(run.rglob('*')):
                if f.is_file():z.write(f,arm+'/'+str(f.relative_to(run)))
            for version in ['1500-v1','1502-v2']:
                failed=diag/f'command-dagger-{arm}-{version}'
                for f in sorted(failed.rglob('*')):
                    if f.is_file() and f.suffix in ['.json','.log','.py']:z.write(f,'failed-starts/'+str(f.relative_to(diag)))
        for name in ['command-dagger-reset-preflight-1452-v2','command-dagger-gradient-reset-1458-v3','command-dagger-resume-zero-1543-v1','command-dagger-resume-gradient-1545-v1']:
            for f in sorted((diag/name).rglob('*')):
                if f.is_file():z.write(f,'runtime/'+str(f.relative_to(diag)))
        for f in [ROOT/'runs/wuji-goal/source-history/pinned-command-dagger-complete-20260923T1504-v3.tar.gz',
                  ROOT/'runs/wuji-goal/source-history/pinned-command-dagger-complete-20260923T1504-v3-manifest.json',
                  ROOT/'scripts/summarize_wuji_command_student_final.py',ROOT/'scripts/wuji_timed_command_metrics.py',Path(__file__),
                  diag/'command-dagger-pair-final-audit-1540.json',out/(prefix+'-all-results.json')]:
            z.write(f,'source-and-audits/'+f.name)
    new=split_archive(archive,out/'dagger-parts')
    old=diag/'release-command-and-sharpa-complete-20260923T1506/wuji-command-absolute-vs-incremental-final-20260923-all-traces-and-models.zip'
    previous=split_archive(old,out/'offline-parts')
    script='''import hashlib,json,sys
from pathlib import Path
m=Path(sys.argv[1]);spec=json.loads(m.read_text());out=m.parent/spec['archive']
assert not out.exists(),out
whole=hashlib.sha256()
with out.open('xb') as f:
 for part in spec['parts']:
  data=(m.parent/part['name']).read_bytes()
  assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest()==part['sha256'],part['name']
  f.write(data);whole.update(data)
assert out.stat().st_size==spec['bytes'] and whole.hexdigest()==spec['sha256']
print('Verified',out)
'''
    (out/'reassemble-wuji-evidence-20260923.py').write_text(script)
    files=[p for p in sorted(out.rglob('*')) if p.is_file() and p!=archive]
    (out/'SHA256SUMS-wuji-dagger-and-offline-parts-20260923.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    (out/'package-status.json').write_text(json.dumps(dict(status='packaged',dagger=new,offline=previous),indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
