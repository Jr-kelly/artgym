"""Plot actual independently rescored hold results and fixed trial-zero traces."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.analysis/'report.json').read_text())
    assert report['status']=='independently_rescored'
    a.output.mkdir(parents=True,exist_ok=False)
    models=['parent','original-final','dense1-final']
    labels=['Parent CP1000','Original reward CP2000','Dense coefficient 1 CP2000']
    colors=['#667085','#2c70b7','#dd7c27']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,source in zip(axes,[3,11]):
        for j,(model,label,color) in enumerate(zip(models,labels,colors)):
            rows=[next(x for x in report['summaries'] if x['source']==source and x['model']==model and x['protocol']==protocol) for protocol in ['fixed2','fixed5']]
            x=np.arange(2)+(j-1)*.24
            y=[100*r['success']/r['n'] for r in rows]
            bars=ax.bar(x,y,.23,label=label,color=color)
            ax.bar_label(bars,labels=[str(r['success'])+'/'+str(r['n']) for r in rows],padding=3,fontsize=8)
        ax.set_title('Source '+str(source));ax.set_xticks([0,1],['2-second commands','5-second commands'])
        ax.set_ylim(0,110);ax.set_yticks([0,25,50,75,100]);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set_ylabel('Strict 20-second success (%)')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
    fig.suptitle('Matched continuation budget: 163,840,000 added interactions per arm')
    fig.tight_layout(rect=[0,.08,1,.96])
    for ext in ['png','pdf']:fig.savefig(a.output/('strict-equal-budget.'+ext),dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,6),sharex=True)
    for i,source in enumerate([3,11]):
        entry=next(x for x in report['inputs'] if x['plan']['row']==source)
        physical=json.loads(Path(entry['path']).read_text())
        for j,protocol in enumerate(['fixed2','fixed5']):
            ax=axes[i,j];ax.axhspan(-2,2,color='#98ce9a',alpha=.3)
            for model,label,color in zip(models,labels,colors):
                item=next(x for x in physical['results'] if x['model']==model and x['protocol']==protocol)
                with np.load(ROOT/item['evidence']/'trace.npz') as trace:
                    error=(trace['slider'][:,0]-trace['goal'][:,0])*1000
                    valid=trace['active'][:,0]&~trace['fall'][:,0]&~trace['invalid'][:,0]
                    error=np.where(valid,error,np.nan)
                    ax.plot(np.arange(len(error))/30,error,label=label,color=color,linewidth=1)
            ax.set_title('Source '+str(source)+' / '+protocol+' / predeclared trial 0')
            ax.set_ylabel('Signed slider error (mm)');ax.grid(alpha=.2)
    for ax in axes[-1]:ax.set_xlabel('Control time (s)')
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
    fig.suptitle('Descriptive time series; green band is ±2 mm, not episode success')
    fig.tight_layout(rect=[0,.05,1,.96])
    for ext in ['png','pdf']:fig.savefig(a.output/('trial-zero-errors.'+ext),dpi=180)
    plt.close(fig)
    (a.output/'manifest.json').write_text(json.dumps(dict(analysis=str(a.analysis),
        trial=0,models=models,scope='Actual frozen physical traces; representative row fixed before results. Counts describe perturbations of two trained source grasps, one continuation seed; no confidence claim across unseen grasps or training seeds.'),indent=2)+'\n')


if __name__=='__main__':main()
