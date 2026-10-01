"""CPU export of existing registered intervention scores; no new success rule."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.analyze_wuji_geometry import read_run
D=Path(__file__).resolve().parent;R=D.parents[1];root=R/'runs/geometry-generalization-20261002';out=D/'intervention-analysis';report=json.loads((out/'report.json').read_text());models={'teacher':'2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8','student':'16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9'};episodes=[]
for label in ['L110','W120']:
 selection=json.loads((root/(label+'-static-confirm64')/'selection.json').read_text())
 for role,prefix in [('legal parent','confirm64-'),('privileged diagnostic after2s','latent-intervention-')]:
  rows=read_run(root/(prefix+label+'-student-F'),selection,models)
  for row in rows:episodes.append(dict(role=role,**row))
with (out/'episodes.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(episodes[0]));w.writeheader();w.writerows(episodes)
fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');rows=report['rows'];names=[r['geometry']+' s'+str(r['source']) for r in rows];x=np.arange(len(rows))
for ax,metric,title in zip(axes,['success','body_stable'],['F complete open-close','Full40s holding']):
 vals=np.array([r[metric]['improvement_pp'] for r in rows]);cis=np.array([r[metric]['paired_bootstrap95_pp'] for r in rows]);bars=ax.bar(x,vals,color=['#228855' if v>=0 else '#bb3344' for v in vals]);ax.errorbar(x,vals,yerr=np.vstack([vals-cis[:,0],cis[:,1]-vals]),fmt='none',color='black',capsize=3);ax.axhline(0,color='grey');ax.set_xticks(x,names,rotation=45,ha='right');ax.set_title(title);ax.set_ylabel('Diagnostic minus legal parent (pp)');ax.set_ylim(-80,80)
 for i,r in enumerate(rows):
  if r['target']:bars[i].set_hatch('//')
fig.suptitle('Same frozen actor/RNN: privileged teacher latent after2s\nNon-deployable diagnostic; paired bootstrap95, N64/source. Hatched = registered targets.');fig.savefig(out/'paired-intervention-effects.png',dpi=180);fig.savefig(out/'paired-intervention-effects.pdf');plt.close(fig)
print('Exported',len(episodes),'existing paired protocol records')
