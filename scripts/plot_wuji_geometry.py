"""Export source-stratified capability and adaptation maps; missing remains visible."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
 p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--runs',type=Path,default=Path('runs/geometry-generalization-20261002'));p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',choices=['screen','confirmation','final'],default='screen');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 d=Path('research/geometry-generalization-20261002');assets=json.loads((d/'ASSETS.json').read_text());labels=list(assets);result=json.loads((a.analysis/'report.json').read_text());rows=result['rows']
 fig,axes=plt.subplots(1,6,figsize=(19,7),sharey=True,layout='constrained')
 for ax,(model,protocol) in zip(axes,[(m,p) for m in ['teacher','student'] for p in ['S2','S5','F']]):
  values=np.full((len(labels),4),np.nan)
  for i,g in enumerate(labels):
   for s in range(4):
    cell=next((r for r in rows if (r['geometry'],r['model'],r['protocol'],r['source'])==(g,model,protocol,s)),None)
    if not cell:
     staticname=('baseline-static-screen-v2' if g=='baseline' else g+'-static-fixed') if a.stage=='screen' else g+('-static-confirm64' if a.stage=='confirmation' else '-static-final');selection=a.runs/staticname/'selection.json'
     if selection.exists() and json.loads(selection.read_text())['sources'][s]['selected']==0:ax.text(s,i,'no grasp',ha='center',va='center',fontsize=6,color='black')
    if cell:
     values[i,s]=cell['rate'];ax.text(s,i,str(cell['success'])+'/'+str(cell['n']),ha='center',va='center',fontsize=7,color='black' if cell['rate']>.5 else 'white')
  cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#dddddd');im=ax.imshow(values,vmin=0,vmax=1,cmap=cmap,aspect='auto');ax.set_title(model+' '+protocol);ax.set_xticks(range(4),['s0','s1','s2','s3']);ax.set_yticks(range(len(labels)),labels)
 fig.colorbar(im,ax=axes,shrink=.7,label='Conditional episode success');fig.suptitle('Frozen policy '+a.stage+': episode counts, conditioned on static-valid initialization; grey = missing/incomplete')
 fig.savefig(a.output/('capability-'+a.stage+'.png'),dpi=180);fig.savefig(a.output/('capability-'+a.stage+'.pdf'));plt.close(fig)
 coverage=np.full((len(labels),4),np.nan);texts={}
 for i,label in enumerate(labels):
  name=(('baseline-static-screen-v2' if label=='baseline' else label+'-static-fixed') if a.stage=='screen' else label+('-static-confirm64' if a.stage=='confirmation' else '-static-final'));path=a.runs/name/'selection.json'
  if not path.exists():continue
  for s in json.loads(path.read_text())['sources']:
   coverage[i,s['source']]=s['static_valid']/s['attempted'];texts[i,s['source']]=str(s['static_valid'])+'/'+str(s['attempted'])
 fig,ax=plt.subplots(figsize=(6,7),layout='constrained');im=ax.imshow(coverage,vmin=0,vmax=1,cmap='Blues',aspect='auto');ax.set_xticks(range(4),['source0','source1','source2','source3']);ax.set_yticks(range(len(labels)),labels)
 for (i,s),text in texts.items():ax.text(s,i,text,ha='center',va='center',color='white' if coverage[i,s]>.65 else 'black')
 ax.set_title(a.stage+' grasp coverage (static-valid / attempted)');fig.colorbar(im,ax=ax,label='Coverage');fig.savefig(a.output/('grasp-coverage-'+a.stage+'.png'),dpi=180);plt.close(fig)
 curves,axs=plt.subplots(1,3,figsize=(15,4),layout='constrained')
 for ax,(axis,idx) in zip(axs,[('L',0),('W',1),('T',2)]):
  series=['baseline']+[axis+str(k) for k in [80,90,110,120]];series=sorted(series,key=lambda g:assets[g]['dimensions_mm_LWT'][idx])
  for model,color in [('teacher','#3366aa'),('student','#cc6633')]:
   for source in range(4):
    chosen=[(assets[g]['dimensions_mm_LWT'][idx],next((r for r in rows if (r['geometry'],r['model'],r['protocol'],r['source'])==(g,model,'F',source)),None)) for g in series];chosen=[(x,r) for x,r in chosen if r]
    if not chosen:continue
    ax.plot([x for x,r in chosen],[r['rate'] for x,r in chosen],marker=['o','s','^','D'][source],color=color,linestyle=['-','--',':','-.'][source],label=model+' s'+str(source))
  ax.set_xlabel(axis+' (mm)');ax.set_ylim(-.05,1.05);ax.axhline(.8,color='grey',linestyle='--');ax.set_title('F functional success, sources separate')
 axs[0].set_ylabel('Conditional success');axs[-1].legend(fontsize=7,bbox_to_anchor=(1.02,1));curves.savefig(a.output/'functional-range.png',dpi=180);plt.close(curves)
 (a.output/'plot-provenance.json').write_text(json.dumps(dict(analysis=str(a.analysis),stage=a.stage,scope='Graph of recorded frozen simulation only; static coverage separate; all cell Wilson95 in accompanying JSON/CSV'),indent=2)+'\n')
if __name__=='__main__':main()
