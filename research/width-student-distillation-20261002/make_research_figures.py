"""Publication artifacts from independently rescored cells and episodes only."""
import argparse,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.record_wuji_width_goal import R,D,record

ROLES=['P','C','G','C_endpoint','G_endpoint','teacher']
NAMES=['P','C +800','G +800','C +3200 (main)','G +3200','teacher']
COLORS=['#777777','#db8b00','#168347','#2456b8','#934b96','#222222']
BASE=R/'runs/width-student-distillation-20261002/analysis'

def cell(report,g,role,protocol,source):
    return next(c for c in report['cells'] if (c['geometry'],c['model'],c['protocol'],c['source'])==(g,role,protocol,source))

def main(final):
    out=R/'runs/width-student-distillation-20261002/figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    one=json.loads((BASE/'window1-complete-dev-v1/report.json').read_text())
    repeats={step:json.loads((BASE/('repeat%d-dev-v1'%step)/'report.json').read_text()) for step in [52000,52800,54400]}
    fig,axs=plt.subplots(1,3,figsize=(14,4),sharey=True)
    for ax,(g,s) in zip(axs,[('W120',3),('baseline',1),('W110',3)]):
        for arm,color in [('C','#db8b00'),('G','#168347')]:
            for seed,style in [(1,'-'),(2,'--')]:
                vals=[]
                for step in [52000,52800,54400]:
                    c=cell(one,g,arm+str(step),'F',s) if seed==1 else cell(repeats[step],g,arm,'F',s)
                    vals.append(c['joint_success']['rate'])
                ax.plot([800,1600,3200],np.array(vals)*100,style,marker='o',color=color,label=arm+' seed'+str(seed))
        ax.axhline(cell(one,g,'P','F',s)['joint_success']['rate']*100,color='#777777',label='P (same dev states)')
        ax.set(title=g+' source'+str(s),xlabel='Added Adam updates',ylim=(0,103),xticks=[800,1600,3200]);ax.grid(alpha=.2)
    axs[0].set_ylabel('F joint success (%)');axs[-1].legend(loc='lower right',fontsize=8)
    fig.suptitle('Two clean-parent optimization streams; n=32/cell, same dev cohort reused across checkpoints')
    fig.tight_layout();fig.savefig(out/'two-seed-dev-learning.png');fig.savefig(out/'two-seed-dev-learning.pdf');plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for seed in [1,2]:
        for arm,color in [('C','#db8b00'),('G','#168347')]:
            path=R/'runs/width-student-distillation-20261002'/(arm+str(seed)+'-window1-h200-17314')/'learning.jsonl'
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            for col,(key,title) in enumerate([('latent_mse','Latent MSE'),('executed_target_mse_rad2','Executed target MSE (rad squared)')]):
                axs[seed-1,col].plot([r['update']-51200 for r in rows],[r[key] for r in rows],color=color,label=arm,linewidth=1)
                axs[seed-1,col].set(title='Seed'+str(seed)+' '+title,xlabel='Added Adam updates');axs[seed-1,col].grid(alpha=.2);axs[seed-1,col].legend()
    fig.suptitle('Training diagnostics; loss is not a behavior selection metric');fig.tight_layout();fig.savefig(out/'training-diagnostics.png');plt.close(fig)
    if final:
        result=json.loads((BASE/'frozen-final-v1/report.json').read_text())
        geometries=['baseline','W110','W120','W115','W115_T110']
        for protocol in ['F','S2','S5']:
            fig,axs=plt.subplots(5,4,figsize=(17,15),sharey=True)
            for row,g in enumerate(geometries):
                for s in range(4):
                    ax=axs[row,s]
                    for i,(role,color) in enumerate(zip(ROLES,COLORS)):
                        c=cell(result,g,role,protocol,s);m=c['joint_success'];low,high=m['wilson95']
                        ax.bar(i,m['rate']*100,color=color,width=.7)
                        ax.errorbar(i,m['rate']*100,yerr=np.maximum(0,np.array([[m['rate']-low],[high-m['rate']]]))*100,color='black',capsize=2,linewidth=.8)
                        ax.text(i,103,str(m['k'])+'/'+str(m['n']),rotation=90,ha='center',va='bottom',fontsize=7)
                    ax.set(title=g+' / source'+str(s),ylim=(0,139),xticks=range(6),xticklabels=['P','C800','G800','C3200','G3200','T']);ax.grid(axis='y',alpha=.15)
                    if s==0:ax.set_ylabel('Joint success (%)')
            fig.suptitle(protocol+' frozen final: episode rates, real denominators, Wilson 95%; C3200 was selected before final')
            fig.tight_layout(rect=[0,0,1,.975]);fig.savefig(out/('final-'+protocol+'-all-sources.png'));fig.savefig(out/('final-'+protocol+'-all-sources.pdf'));plt.close(fig)
        episodes=list(csv.DictReader((BASE/'frozen-final-v1/episodes.csv').open()))
        fig,axs=plt.subplots(2,3,figsize=(15,8),sharex=True,sharey=True)
        for ax,(g,s) in zip(axs.flat,[('baseline',1),('W110',3),('W120',3),('W115',3),('W115_T110',3)]):
            for role,color,name in zip(ROLES,COLORS,NAMES):
                rows=[r for r in episodes if (r['geometry'],r['model'],r['protocol'],int(r['source']))==(g,role,'F',s)]
                t=np.array([float(r['first_body_breach_s']) if r['first_body_breach_s'] else np.inf for r in rows]);grid=np.arange(0,40.01,.1)
                ax.plot(grid,100*np.mean(t[:,None]>grid,axis=0),color=color,label=name)
            ax.axvline(20,color='#c78b00',linestyle='--');ax.set(title=g+' source'+str(s),xlabel='Simulation time (s)',ylabel='Still within body thresholds (%)',ylim=(0,103));ax.grid(alpha=.2)
        axs.flat[-1].axis('off');handles,labels=axs.flat[0].get_legend_handles_labels();axs.flat[-1].legend(handles,labels,loc='center')
        fig.suptitle('Raw first body breach/fall timing; 20s line marks training horizon, not a causal attribution')
        fig.tight_layout();fig.savefig(out/'final-first-instability.png');fig.savefig(out/'final-first-instability.pdf');plt.close(fig)
    record('standard_research_figures_generated',evidence=str(out.relative_to(R)),includes_final=final,next='Inspect axes, denominators and first-breach curves; publish standalone plots with raw tables')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');a=p.parse_args();main(a.final)
