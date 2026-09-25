"""Package independently rescored final results, including unsuccessful policies."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    base=ROOT/'runs/wuji-goal';diag=base/'diagnostics'
    out=diag/'release-command-and-sharpa-complete-20260923T1506'
    out.mkdir(exist_ok=False)
    command=json.loads((diag/'absolute-target-final-rescored-1458-v2.json').read_text())
    sharpa=json.loads((diag/'sharpa-final100-rescored-1457.json').read_text())
    assert command['all12_rescored'] and sharpa['all10_cycle_matrices_rescored']
    prefix='wuji-command-absolute-vs-incremental-final-20260923'
    shutil.copy2(diag/'absolute-target-final-rescored-1458-v2.json',out/(prefix+'-results.json'))
    fig,axes=plt.subplots(1,3,figsize=(12,3.8),layout='constrained')
    for ax,key,label in zip(axes,['joint','body','endpoints'],['All criteria','Body stability only','All command endpoints']):
        for arm,color in [('absolute','tab:blue'),('incremental','tab:orange')]:
            for seconds,style in [(2,'-'),(5,'--')]:
                rows=sorted([r for r in command['rows'] if r['arm']==arm and r['seconds']==seconds],key=lambda r:r['update'])
                ax.plot([r['update'] for r in rows],[100*r[key]/300 for r in rows],style,color=color,marker='o',label=f'{arm}, {seconds}s')
        ax.set(title=label,xlabel='Offline fitting update',ylim=(-2,102),ylabel='Development success (%)')
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle('Wuji: 3 training grasps × 100 reused perturbations; 20 s frozen evaluation')
    fig.savefig(out/(prefix+'-curves.png'),dpi=180);fig.savefig(out/(prefix+'-curves.pdf'));plt.close(fig)
    run=diag/'absolute-target-eval-0110-v3';fit=diag/'absolute-target-0048-v2'
    source=base/'source-history/pinned-absolute-target-eval-source-20260923T0110-v3.tar.gz'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='c54997353ad831f358c1d9a8dbe9bc9ff42a9f8d757d9e04f08e7690381290a7'
    with zipfile.ZipFile(out/(prefix+'-all-traces-and-models.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in sorted(run.rglob('*')):
            if p.is_file():z.write(p,'formal/'+str(p.relative_to(run)))
        for p in sorted(fit.glob('gate-*/command-student-audit.json')):
            z.write(p,'runtime/'+str(p.relative_to(fit)))
        z.write(fit/'status.json','original-stopped-pipeline.json')
        for p in sorted((fit/'fitting').iterdir()):
            if p.suffix in ['.json','.pth']:z.write(p,'fitting/'+p.name)
        for p in [source,ROOT/'scripts/summarize_wuji_command_student_final.py',ROOT/'scripts/wuji_timed_command_metrics.py',Path(__file__)]:
            z.write(p,'source/'+p.name)
        z.write(diag/'absolute-target-final-rescored-1458-v2.json','independent-rescore.json')
    text='''Final Wuji command-policy comparison (failed task outcome)

Both 116→256→128→20 MLPs fit identical frozen-teacher data for 1000 Adam updates.
Absolute commands score 0/300 for both clocks; incremental commands score 9/300
at 2s and 10/300 at 5s. Fourth grasp: 0/32 for both final models. All 12 frozen
conditions and complete physical/prediction traces are included; no selection
of intermediate peaks. Offline fitting errors are not task success.

Joint success: each scheduled endpoint within 2 mm for its final 9 frames;
body translation <10 mm and rotation <0.25 rad throughout; 600 valid frames.
Body-only curves are independently computed from pose traces, not stable_full,
which also demands a first successful open/close cycle. The earlier unpublished
1457 rescore used that compound field for body; this report corrects the label
without changing any joint-task outcome.

The original runtime gate stopped on a 4.77e-6 normalized-action difference
between zero-output heads. Actual applied joint targets and physics were exactly
equal. Evaluation V3 verified that equality and retained the existing <1e-6 rad
command tolerance; it did not change weights, control, success criteria or data.
This is a Wuji transfer experiment, not the paper student architecture. All
initial states have been observed and are development data. No new independent,
new-geometry or hardware success is claimed. Full teacher-label dataset and
earlier failure evidence were published in the previous runtime package.
'''
    (out/(prefix+'-README.txt')).write_text(text)
    prefix='sharpa-teacher-cp2100-student-cp1000-final100-20260923'
    shutil.copy2(diag/'sharpa-final100-rescored-1457.json',out/(prefix+'-results.json'))
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for offset,row,color in [(-.18,sharpa['rows'][0],'tab:blue'),(.18,sharpa['rows'][1],'tab:orange')]:
        groups=row['groups'];ax.bar([i+offset for i in range(5)],[100*g['success']/g['total'] for g in groups],width=.36,label=row['arm'],color=color)
    ax.set(xticks=list(range(5)),xticklabels=[g['instance'] for g in sharpa['rows'][0]['groups']],ylim=(0,100),ylabel='Execution success (%)',xlabel='Previously observed held-out training geometry',title='Sharpa: 287 grasps × 100 randomized episodes per policy')
    ax.legend();ax.grid(axis='y',alpha=.25)
    fig.savefig(out/(prefix+'-comparison.png'),dpi=180);fig.savefig(out/(prefix+'-comparison.pdf'));plt.close(fig)
    run=diag/'sharpa-final100-0056-v1'
    source=base/'source-history/pinned-sharpa-final100-source-20260923T0056-v1.tar.gz'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='48e6fb339e5846bc5bf443dddf77ec79d90a5b818d7a52bc2904ebf8198a5cb6'
    with zipfile.ZipFile(out/(prefix+'-complete-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(run.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(run)))
        for p in [source,ROOT/'scripts/summarize_sharpa_final100.py',Path(__file__)]:z.write(p,'source/'+p.name)
        z.write(diag/'sharpa-final100-rescored-1457.json','independent-rescore.json')
    (out/(prefix+'-README.txt')).write_text('''Matched final evaluation: teacher 14472/28700 (50.43%), student 13065/28700
(45.52%). Teacher CP2100 is fixed; student CP1000 completed 1000 updates and
65,536,000 training actions. All 10 per-geometry cycle matrices were rescored.
Each of 287 grasps received 100 randomized 40-second executions per policy.
Success uses the paper-style 10 mm arrival-based full-cycle metric, with no
automatic selection of five successful grasps. These are five geometries held
out of fitting, but previously observed during development; this is not a fresh
geometry blind test. This does not complete the teacher's 2-billion-frame target
and cannot be directly compared to Wuji's stricter timed 2 mm criterion.
''')
    files=sorted(out.iterdir())
    (out/'SHA256SUMS-command-and-sharpa-final-20260923T1506.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
