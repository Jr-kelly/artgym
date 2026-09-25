"""Publish completed normalization, settled-grasp and student comparisons."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]
    base=root/'runs/wuji-goal'
    output=base/'release-adaptation-progress-20260922'
    output.mkdir(parents=True,exist_ok=True)
    prefix='wuji-knife-adaptation-progress-20260922'
    sources={}

    def read(path):
        sources[str(path.relative_to(root))]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                                data=json.loads(path.read_text()))
        return sources[str(path.relative_to(root))]['data']

    def report(name):
        path=base/'verification'/name
        status=read(path/'status.json');assert status['status']=='completed' and status['returncode']==0
        result=read(path/'report.json');assert result['num_envs']==100 and result['recorded_steps']==600
        return result

    normalization={}
    for policy in ['original-frozen10','centered-warmstart']:
        normalization[policy]={str(seconds):report(f'damping3-{policy}-timed{seconds}seconds-perturb100') for seconds in [2,5]}
    ids={v['initial_states_sha256'] for rows in normalization.values() for v in rows.values()}
    assert len(ids)==1
    centered=read(base/'diagnostics/damping3-centered-warmstart/policy/manifest.json')
    settled=read(base/'diagnostics/lowgain-settled-grasps-v1/joined-quality-report.json')
    read(base/'diagnostics/lowgain-settled-grasps-v1/status.json')
    read(base/'diagnostics/lowgain-settled-grasps-v1/candidates/manifest.json')
    read(base/'diagnostics/lowgain-settled-grasps-v1/candidates/static/report.json')
    read(base/'diagnostics/lowgain-settled-grasps-v1/semantic-contacts/report.json')
    students={arm:{str(cp):{str(t):report(f'student-official-timed10-{arm}-cp{cp}-timed{t}seconds-perturb100')
                         for t in [2,5]} for cp in [200,300,500]} for arm in ['warm200','control']}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.8),constrained_layout=True)
    for ax,(key,title) in zip(axes,[('first_cycle_strict','Stable first open-close cycle'),
                                  ('stable_full_all_endpoints','Every endpoint held + full 20 s stability')]):
        for offset,policy,label,color in [(-.19,'original-frozen10','Original frozen teacher','#4678b5'),
                                        (.19,'centered-warmstart','Damping-centered policy','#2b9278')]:
            bars=ax.bar(np.arange(2)+offset,[normalization[policy][str(t)][key] for t in [2,5]],width=.38,color=color,label=label)
            ax.bar_label(bars)
        ax.set(xticks=[0,1],xticklabels=['2 s commands','5 s commands'],ylim=(0,110),ylabel='Trials passing / 100',title=title)
        ax.legend(fontsize=8)
    fig.suptitle('Actual = observed damping 3 N s/m | same 100 development initial states\nOnly one normalization mean changed; learned weights unchanged; before adaptation training',fontsize=11)
    fig.savefig(output/(prefix+'-normalization.png'),dpi=160);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    labels=['Source\ngrasps','Survive\nsettling','Stable\n20 s','+ Posture\nclosed, reach','+ Five-pad\ncontacts']
    for ax,split,denom in zip(axes,['train','test'],[33,5]):
        rows=[r for r in settled['records'] if r['split']==split]
        values=[len(rows),sum(r['restarted'] for r in rows),sum(r['static_stable20s'] for r in rows),
                sum(r['restarted'] and r['static_stable20s'] and r['posture_pass'] and r['slider_closed'] and r['thumb_reach']['passed'] for r in rows),
                sum(r['all_gates_pass'] for r in rows)]
        bars=ax.bar(range(5),values,color=['#4678b5']*4+['#2b9278']);ax.bar_label(bars)
        ax.set(xticks=range(5),xticklabels=labels,ylim=(0,denom*1.22),ylabel='Number of grasps',title=f'Original {split} split: {denom} source grasps')
    fig.suptitle('New low-gain states after 2 s passive settling | old split assignments retained\nIndependent restart: GPU holding for 20 s, CPU semantic contacts for 2 s | no policy actuation',fontsize=11)
    fig.savefig(output/(prefix+'-settled-grasps.png'),dpi=160);plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(11.6,7.3),constrained_layout=True)
    for column,t in enumerate([2,5]):
        for row,(key,label) in enumerate([('first_cycle_strict','Stable first cycle / 100'),('stable_full_all_endpoints','Full stable + all held / 100')]):
            ax=axes[row,column]
            for arm,title,color in [('warm200','Teacher drives first 200 updates','#2b9278'),('control','Student drives all updates','#4678b5')]:
                vals=[students[arm][str(cp)][str(t)][key] for cp in [200,300,500]]
                ax.plot([200,300,500],vals,'o-',label=title,color=color)
                for cp,value in zip([200,300,500],vals):ax.annotate(str(value),(cp,value),xytext=(4,4),textcoords='offset points',fontsize=9,color=color)
            ax.set(xticks=[200,300,500],xlabel='Training updates',ylabel=label,title=f'{t} s commands',ylim=(-1,105 if row==0 else 20))
            if row==0:ax.legend(fontsize=8)
    fig.suptitle('Every evaluation is driven independently by the student | 20 s, same 100 initial states\nSame seed, actor, encoder initialization, optimizer and budget; one training seed',fontsize=11)
    fig.savefig(output/(prefix+'-student-sampling.png'),dpi=160);plt.close(fig)

    payload=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources=sources)
    (output/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(payload,indent=2)+'\n')
    (output/(prefix+'-results.md')).write_text('''# Wuji adaptation progress, 2026-09-22

The normalization comparison uses the same 100 development initial states, actual and observed slider damping 3 N s/m, official Wuji joint gains and ArtBot geometry in PhysX. The modified policy translates only the damping normalization mean from 0.3 to 3. It keeps all learned weights, variances and counts. This is an explicitly changed policy, with a new SHA256, evaluated before adaptation training. No false damping is supplied to the policy. It is not hardware calibration or an improvement established on new grasps.

Stable first-cycle success requires the two slider endpoints to be attained within 2 mm for 0.3 s, with stable body pose. Joint success additionally requires every command window to end with 0.3 s within tolerance and body displacement/rotation below 10 mm/0.25 rad throughout 20 s. The full trial records include all failures.

Settled grasps are newly generated initial states using a preload setting previously selected on the 33 training grasps. Every surviving candidate was independently restarted. All quality gates passed for 17 of the 33 original training sources and zero of the five held-out sources. This is static feasibility, not learned manipulation; none of the old failed validation trials was recentered or removed. Fresh-seed generation of 1,000 additional candidates is separate and is not included as a completed result here.

The student comparison fixes seed 20261013, 1,024 environments, 500 updates, rollout 16, learning rate 1e-4, and latent MSE plus 0.1 cosine loss. One arm uses teacher actions for the first 200 updates; the other always uses student actions. All plotted evaluations use independent student control. The teacher prefix has no demonstrated sustained-holding advantage. Both late checkpoints regress on important measures; earlier checkpoints remain available. A third arm using teacher sampling throughout is running and is excluded from these completed comparisons.

This work still needs stronger holding, new-grasp and geometry evaluation, a robust student, and real control/contact/object calibration. The original Sharpa reference, reward-corrected and upstream experiments remain separate.
''')
    files=sorted(output.glob(prefix+'-*'))
    (output/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files if p.suffix!='.txt'))
    print(output)


if __name__=='__main__':main()
