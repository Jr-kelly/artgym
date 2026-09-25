"""Plot measured robustness and grasp coverage; never infer success from reward."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    sources={}
    def read(path):
        path=ROOT/path;sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())
    prefix='runs/wuji-goal/verification/'
    nominal=[read(prefix+n+'/report.json') for n in ['precision-ft-cp10-trace100','student-precision-cp100-trace100','student-precision-cp125-trace100']]
    noisy=[read(prefix+n+'/report.json') for n in ['precision-teacher-cp10-perturb-small','student-precision-cp100-perturb-small','student-precision-cp125-perturb-small']]
    labels=['Teacher CP10','Student CP100','Student CP125']
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,title,rows in zip(axes,['Nominal initial grasp','Perturbed initial grasp'],[nominal,noisy]):
        x=np.arange(3)
        for offset,key,label,color in [(-.18,'successful_trials','Complete open-close','#3973ac'),(.18,'strict_first_cycle_trials','Complete + stable first cycle','#d7912b')]:
            y=[r[key] for r in rows];bars=ax.bar(x+offset,y,width=.34,label=label,color=color)
            ax.bar_label(bars,padding=3,fontsize=10)
        ax.set_xticks(x,labels);ax.set_ylim(0,114);ax.set_title(title);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set_ylabel('Passed trials / 100');axes[0].legend(loc='lower left',fontsize=9)
    fig.suptitle('Wuji knife: 2 mm goal tolerance, 0.3 s continuous dwell',fontsize=14)
    fig.text(.5,.015,'Perturbations: position ±0.5 mm/axis, joints ±0.01 rad, rotation vector ±0.5°/axis. Same 100 initial states for all policies.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.94]);fig.savefig(a.output/'wuji-knife-teacher-student-robustness-20260922.png',bbox_inches='tight',pad_inches=.12);plt.close(fig)
    train=read(prefix+'fingertip-cp100-training33/summary.json')
    val=read('runs/wuji_acq_fingertip000_ft_v2/evaluation/monitor/epoch_000100/000.json')
    train_rate=(np.asarray(train['consecutive_success_cycles_trials'])>=1).mean(0)
    val_rate=(np.asarray(val['consecutive_success_cycles_trials'])>=1).mean(0)
    fig,axes=plt.subplots(2,1,figsize=(11,6),gridspec_kw={'height_ratios':[1.4,1]})
    axes[0].bar(np.arange(33),100*train_rate,color=['#d7912b' if i==29 else '#3973ac' for i in range(33)])
    axes[0].set_xticks(np.arange(33));axes[0].set_ylabel('Success (%)');axes[0].set_ylim(0,115)
    axes[0].set_title('Training grasps: 119/132 trials; four trials per grasp')
    axes[0].text(29,105,'29',ha='center',color='#a66500');axes[0].set_xlabel('Original training grasp index (29: rare bent-thumb posture)')
    bars=axes[1].bar(np.arange(5),100*val_rate,color='#748897',width=.55)
    axes[1].bar_label(bars,labels=[f'{round(v*10)}/10' for v in val_rate],padding=3)
    axes[1].set_xticks(np.arange(5));axes[1].set_ylim(0,115);axes[1].set_ylabel('Success (%)')
    axes[1].set_title('Held-out validation grasps: 34/50 trials');axes[1].set_xlabel('Original validation grasp index')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Multi-grasp teacher CP100: at least one full cycle in 20 seconds',fontsize=14)
    fig.text(.5,.015,'One geometry, 5 mm tolerance, no dwell. Repeated validation used for model selection; not a final blind test.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.035,1,.94]);fig.savefig(a.output/'wuji-knife-grasp-coverage-cp100-20260922.png',bbox_inches='tight',pad_inches=.12);plt.close(fig)
    (a.output/'wuji-knife-robustness-provenance-20260922.json').write_text(json.dumps(sources,indent=2)+'\n')


if __name__=='__main__':main()
