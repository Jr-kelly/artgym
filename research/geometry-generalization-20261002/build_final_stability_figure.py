"""Final report figure; reads independent scoring, never modifies evaluation."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
rows=json.loads((D/'final-analysis/report.json').read_text())['rows'];labels=list(json.loads((D/'ASSETS.json').read_text()));out=D/'figures/final';out.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,4,figsize=(14,7),sharey=True,layout='constrained')
for ax,(model,metric,count) in zip(axes,[(m,k,c) for m in ['teacher','student'] for k,c in [('body_rate','body_stable'),('success_and_full_stability_rate','success_and_full_stability')]]):
 values=np.full((len(labels),4),np.nan)
 for i,g in enumerate(labels):
  for source in range(4):
   cell=next((r for r in rows if (r['geometry'],r['model'],r['protocol'],r['source'])==(g,model,'F',source)),None)
   if cell:
    values[i,source]=cell[metric];ax.text(source,i,f"{cell[count]}/{cell['n']}",ha='center',va='center',fontsize=8,color='black' if values[i,source]>.5 else 'white')
   else:ax.text(source,i,'no grasp',ha='center',va='center',fontsize=7)
 cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#dddddd');im=ax.imshow(values,vmin=0,vmax=1,cmap=cmap,aspect='auto');ax.set_xticks(range(4),['s0','s1','s2','s3']);ax.set_yticks(range(len(labels)),labels);ax.set_title(model+('\n40s holding' if metric=='body_rate' else '\nF success AND 40s holding'))
fig.colorbar(im,ax=axes,shrink=.7,label='Conditional episode fraction');fig.suptitle('Independent final: functional success does not imply full-horizon holding')
fig.savefig(out/'F-holding-and-joint-success.png',dpi=180);fig.savefig(out/'F-holding-and-joint-success.pdf');plt.close(fig)
