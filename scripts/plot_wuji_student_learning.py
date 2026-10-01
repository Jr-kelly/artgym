"""Separate changing-behavior fitting curves from frozen closed-loop checkpoint scores."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,default=Path('runs/unified-student-20261001'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 fig,axes=plt.subplots(2,2,figsize=(12,8));colors={'S0':'#2266bb','C1':'#b85c19','SC-real':'#218c55','SC-masked':'#9257b5','SA-real':'#c83737'}
 folders={'S0':['S0-3200'],'C1':['C1-3200'],'SC-real':['SC-real-6400','SC-real-12800','SC-real-25600','SC-real-38400'],'SC-masked':['SC-masked-6400-r1','SC-masked-12800'],'SA-real':['SA-real-12800','SA-real-25600','SA-real-38400']}
 for model in colors:
  paths=[a.runs/folder/'learning.jsonl' for folder in folders[model]]
  rows=[json.loads(line) for path in paths if path.exists() for line in path.read_text().splitlines()]
  if not rows:continue
  x=np.array([r['update'] for r in rows]);loss=np.array([r['latent_mse'] for r in rows])
  smooth=[loss[(x>step-100)&(x<=step)].mean() for step in x]
  axes[0,0].plot(x,smooth,label=model,color=colors[model])
  measured=[r for r in rows if r['target_mse_rad2'] is not None]
  axes[0,1].plot([r['update'] for r in measured],[r['target_mse_rad2'] for r in measured],label=model,color=colors[model],alpha=.8)
 for protocol,ax in [('S2',axes[1,0]),('S5',axes[1,1])]:
  for model in colors:
   points=[]
   for d in a.runs.glob(model+'-*-development'):
    try:step=int(d.name[len(model)+1:-len('-development')])
    except ValueError:continue
    p=d/(model+'-'+str(step)+'-'+protocol)/'report.json'
    if not p.exists():continue
    r=json.loads(p.read_text())['records'];n=len(r)//4
    rates=[sum(x['stable_full_all_endpoints'] for x in r[s*n:(s+1)*n])/n for s in range(4)]
    points.append((step,min(rates)))
   if points:
    points.sort();ax.plot(*zip(*points),marker='o',label=model,color=colors[model])
  ax.axhline(.8,color='black',linestyle='--',linewidth=1,label='absolute S threshold');ax.set_ylim(-.03,1.03);ax.set_title(protocol+' frozen development: worst source strict rate');ax.set_ylabel('Episode success proportion')
 axes[0,0].set_title('Changing student-behavior latent MSE (100-update window)');axes[0,0].set_ylabel('MSE; distributions differ across methods');axes[0,0].set_yscale('log')
 axes[0,1].set_title('Executed joint-target counterfactual error');axes[0,1].set_ylabel('MSE (rad²)');axes[0,1].set_yscale('log')
 for ax in axes.flat:ax.set_xlabel('Actual optimizer steps');ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('Wuji initial-calibration-conditional student — development only',fontsize=13);fig.tight_layout()
 fig.savefig(a.output/'learning-curves.png',dpi=160);fig.savefig(a.output/'learning-curves.svg');plt.close(fig)
if __name__=='__main__':main()
