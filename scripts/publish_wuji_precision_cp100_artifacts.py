"""Prepare text-free policy video and measured precision/robustness figures."""
import hashlib
import json
import shutil
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal/verification'
    video=base/'precision-near01-cp100-preset3-video';v=json.loads((video/'report.json').read_text())
    ids=['precision-near01-cp50-perturb-small','precision-near01-cp100-perturb-small',
         'precision-near1-cp100-perturb-small','precision-near01-cp100-blind-seed3179-perturb100',
         'precision-near01-cp100-blind-seed4207-perturb100']
    reports=[json.loads((base/name/'report.json').read_text()) for name in ids]
    assert all(r['envs']==100 for r in reports)
    assert all(reports[j]['checkpoint_sha256']==v['checkpoint_sha256'] for j in [1,3,4])
    out=root/'runs/wuji-goal/release-precision-cp100-20260922-0325';out.mkdir(exist_ok=True)
    prefix='wuji-knife-precision-near01-cp100-20260922'
    shutil.copyfile(video/'policy.mp4',out/(prefix+'-three-perturbed-states-no-text.mp4'))
    reader=imageio.get_reader(video/'policy.mp4');meta=reader.get_meta_data();frames=reader.count_frames()
    assert frames==600 and meta['fps']==30 and meta['size']==(1536,384)
    for name,index in [('initial',0),('midpoint',300),('final',599)]:
        imageio.imwrite(out/(prefix+'-'+name+'.png'),reader.get_data(index))
    reader.close()
    labels=['Near .1\nCP50','Near .1\nCP100','Near 1\nCP100','CP100\nseed3179','CP100\nseed4207']
    fig,ax=plt.subplots(figsize=(11,4.8))
    keys=['successful_trials','strict_first_cycle_trials','stable_full_rollout_trials']
    for j,(key,label,color) in enumerate(zip(keys,['Complete cycle','Stable first cycle','Stable full20s'],['#287ca7','#559c69','#c8893b'])):
        x=np.arange(len(reports))+(j-1)*.24;values=[r[key] for r in reports]
        bars=ax.bar(x,values,.22,label=label,color=color)
        for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,value+1,str(value),ha='center',fontsize=8)
    ax.axvline(2.5,color='#666666',linestyle='--',linewidth=1)
    ax.set_xticks(np.arange(5),labels);ax.set_ylim(0,118);ax.set_yticks([0,25,50,75,100])
    ax.set_ylabel('Trials meeting criterion /100');ax.set_title('Precise Wuji knife: development comparison and two fresh perturbation seeds')
    ax.legend(loc='upper center',ncol=3,fontsize=9);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    fig.text(.02,.02,'Same prescribed grasp, position±0.5mm/axis, joints±0.01rad, rotation-vector±0.5deg/axis.\n'
        'Goals:2mm tolerance +0.3s dwell. Stable base:<10mm translation,<0.25rad rotation. No hardware/unseen-geometry claim.',fontsize=9)
    fig.tight_layout(rect=[0,.105,1,1]);fig.savefig(out/(prefix+'-robustness.png'),dpi=160);plt.close(fig)
    table='\n'.join('|'+label.replace('\n',' ')+'|'+'|'.join(str(r[key]) for key in keys)+'|' for label,r in zip(labels,reports))
    notes='''# Wuji precision policy CP100

This video uses learned closed-loop actions from a frozen teacher. No demonstration
trajectory is supplied. The knife base is free and the slider passive. Dimensions
remain147x19x11mm and total mass35g, with uncalibrated slider damping0.3.

Three panels from left to right are saved perturbation rows0,2,76, declared before
recording. The20-second local4090 video has600frames at30fps,1536x384,with no text
overlays. These are three perturbations of one nominal grasp, not three distinct
grasp families or objects. All three finish precise opening/closing; the left and
middle panels later exceed the0.25rad pose limit. The video preserves this drift.
Local cycle counts are9,9,12; strict first-cycle3/3,full-rollout stability1/3.

IndependentH100evaluations (each denominator100):

| Policy / seed | Complete cycle | Stable first cycle | Stable full20s |
|---|---:|---:|---:|
'''+table+'''

The first three columns of the figure use the exact same development perturbations
(seed1616). The final two groups use newly declared seeds3179and4207, which were not
used to choose this checkpoint. All three evaluation sets use the same small-noise
distribution and the same nominal grasp. This does not establish generalization to
other grasp families, unknown geometry, large initialization errors or hardware.

Stable means base displacement<10mm and rotation<0.25rad. Full-rollout stability
also requires surviving all20seconds without fall/invalid/goal-timeout. The source
teacherCP10 scored63complete/60first-stable/26full-stable on seed1616. Goal tolerances
remain2mm with0.3seconds continuous dwell. Additional continuous-cycle and absolute
pose-cost training is queued to address later failures.
'''
    (out/(prefix+'-results.md')).write_text(notes)
    files=[video/'report.json']+[base/name/'report.json' for name in ids]
    provenance=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        checkpoint_sha256=v['checkpoint_sha256'],saved_initial_states=v['saved_initial_states'],
        video=dict(frames=frames,fps=30,width=1536,height=384,no_text_overlay=True),
        sources=[dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    sums=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(out.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sums)+'\n');print(out)


if __name__=='__main__':main()
