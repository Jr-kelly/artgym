"""Package completed holding-timing and multi-grasp input-distribution evidence."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    destination=base/'release-holding-phase-20260922';destination.mkdir(parents=True,exist_ok=True)
    prefix='wuji-knife-holding-phase-20260922'
    phase=json.loads((base/'diagnostics/holding-departure-phase-20260922.json').read_text())
    runtime=json.loads((base/'diagnostics/functional20-runtime-v2/report.json').read_text())
    completion=json.loads((base/'diagnostics/functional20-runtime-v2/status.json').read_text())
    assert completion['status']=='completed' and completion['returncode']==0 and runtime['status']=='passed'
    identities={};reports={}
    for name,record in phase['results'].items():
        p=base/'verification'/name/'report.json';report=json.loads(p.read_text())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==record['input_sha256']['report.json']
        reports[name]=report;identities[name]=report['checkpoint_sha256']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(15.2,4.9),constrained_layout=True)
    for i,t in enumerate([2,5]):
        for offset,arm,color in [(-.18,'fixed','#4678b5'),(.18,'variable','#2b9278')]:
            row=reports[f'official-duration-{arm}-cp25-timed{t}seconds-perturb100']
            bars=axes[0].bar(i+offset,row['stable_full_all_endpoints'],width=.36,color=color,label=arm if i==0 else None)
            axes[0].bar_label(bars)
    axes[0].set(xticks=[0,1],xticklabels=['2 s eval','5 s eval'],ylim=(0,110),ylabel='Joint successes / 100',title='Matched CP25: every endpoint + full stable')
    axes[0].legend(title='Training duration')
    for ax,t in zip(axes[1:],[2,5]):
        for arm,color in [('fixed','#4678b5'),('variable','#2b9278')]:
            record=phase['results'][f'official-duration-{arm}-cp25-timed{t}seconds-perturb100']
            rows=[r for r in record['records'] if r['command']=='close' and r['attained'] and r['alive_whole_stage'] and r['pose_stable_whole_stage']]
            times=[r['sustained_toward_next_seconds'] for r in rows if r['sustained_toward_next_seconds'] is not None]
            bins=np.linspace(0,t,11)
            hist,_=np.histogram(times,bins)
            ax.step(bins[:-1],hist/max(1,len(rows))*100,where='post',color=color,label=f'{arm}: {len(times)}/{len(rows)} windows')
        ax.set(xlim=(0,t),xlabel='Time from close command (s)',ylabel='Windows in bin / stable arrivals (%)',title=f'Sustained reopening, {t} s eval')
        ax.legend(fontsize=8)
    fig.suptitle('Same seed, CP10 initialization and 25 training epochs | same 100 development initial states\nFixed 2 s versus randomly sampled 2/5 s training commands; window counts are not independent trials',fontsize=11)
    fig.savefig(destination/(prefix+'-duration-comparison.png'),dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.8),constrained_layout=True)
    for t,color in [(2,'#4678b5'),(5,'#2b9278')]:
        rec=phase['results'][f'official-duration-fixed-cp100-timed{t}seconds-perturb100']
        rows=[r for r in rec['records'] if r['command']=='close' and r['attained'] and r['alive_whole_stage'] and r['pose_stable_whole_stage']]
        times=[r['sustained_toward_next_seconds'] for r in rows if r['sustained_toward_next_seconds'] is not None]
        axes[0].hist(times,bins=np.linspace(0,5,31),weights=np.ones(len(times))/len(rows)*100,histtype='step',linewidth=2,color=color,label=f'{t} s eval: {len(times)}/{len(rows)} windows')
    axes[0].set(xlim=(0,5),xlabel='Time from close command (s)',ylabel='Windows in bin / stable arrivals (%)',title='Fixed-clock CP100: reopens around 1.23 s')
    axes[0].legend(fontsize=8)
    blocks=runtime['normalization']['blocks'];labels=['Policy input','Privileged input','Critic contact']
    vals=[blocks[k]['reset_clipped_fraction']*100 for k in ['policy','privileged','critic_contact']]
    bars=axes[1].bar(range(3),vals,color='#4678b5');axes[1].bar_label(bars,fmt='%.1f%%')
    axes[1].set(xticks=range(3),xticklabels=labels,ylim=(0,60),ylabel='Input elements clipped at reset (%)',title='Single-grasp normalizer on functional20')
    fig.suptitle('Timing is consistent with an internal policy pattern; it does not uniquely prove anticipation\nInput clipping is descriptive; normalizer-count training comparison is separate and ongoing',fontsize=11)
    fig.savefig(destination/(prefix+'-timing-and-input-shift.png'),dpi=160);plt.close(fig)
    paths=[base/'diagnostics/holding-departure-phase-20260922.json',base/'diagnostics/functional20-runtime-v2/report.json',
        base/'diagnostics/functional20-runtime-v2/status.json',base/'diagnostics/functional20-count1-warmstart/manifest.json',
        base/'functional20-dataset-manifest.json',base/'diagnostics/functional20-grasp-separation.json']
    payload=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        records={str(p.relative_to(root)):json.loads(p.read_text()) for p in paths},reports=reports,
        sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (destination/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(payload,indent=2)+'\n')
    (destination/(prefix+'-results.md')).write_text('''# Holding timing and multi-grasp input shift

At matched CP25 and seed 20261015, random 2/5-second training durations yield 55/100 joint successes with 2-second evaluation commands and 50/100 with 5-second commands. The fixed-duration control yields 38/100 and 31/100. Joint success requires every endpoint to be held within 2 mm for the last 0.3 seconds and knife pose to stay within 10 mm/0.25 rad for the whole 20 seconds. Both start from the same teacher and have the same 25-epoch transition budget. Command counts and reward opportunities differ with command duration. These are one nominal grasp's perturbations and one training seed, not new-grasp generalization or a final improvement over the best frozen teacher.

The timing histograms include only closing command windows that reached the endpoint and remained alive with stable knife pose throughout that window. Reopening requires at least 0.3 seconds more than 2 mm toward the next endpoint. A trial can contain several windows; window counts are not independent trials. Reopening can occur transiently and recover before the command ends. All omitted-from-histogram failed or unreached windows remain in the JSON records.

The later fixed-duration CP100 reopens at a median 1.23 seconds under both 2- and 5-second external commands. This timing is consistent with an internal policy pattern that fails to wait for the next command. It does not uniquely distinguish anticipation, recurrent memory, feedback failure or contact mechanics. The random-duration CP25 reduces closing failures but increases some opening failures; later CP50 also regresses. No solved-holding claim is made.

The functional20 runtime gate checked 10,000 actual PhysX transitions, sampled every one of the 20 training-source rows, verified the actual official joint gains, object damping, learned-action mapping and command switches. The held-out split was lazily unloaded during training. A frozen single-grasp normalizer clips about 42.6% of policy-input elements and 25.5% of privileged elements at reset. This is a measured distribution mismatch, not proof that it is the sole source of failure.

The new normalization-count comparison changes only the initial count from 39,321,601 to 1. It preserves learned weights, means and variances and has identical frozen normalization before training. Both arms start fresh Adam and counters and receive identical dataset, seed, learning rate and budget. Formal comparison results are pending. Functional20 consists of 17 earlier training-source settled grasps plus three new training grasps and one new held-out grasp. Its test pose has no near-duplicate training pose under the existing 5 mm/0.05 rad diagnostic thresholds. One held-out grasp is still too small a generalization test. Old failed validation sources remain separate and unchanged.
''')
    files=sorted(destination.glob(prefix+'-*'))
    (destination/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files if p.suffix!='.txt'))
    print(destination)


if __name__=='__main__':main()
