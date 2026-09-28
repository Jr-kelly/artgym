"""Plot per-base frozen outcomes without pooling perturbations as new grasps."""
import argparse,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args()
    with (a.analysis/'per-grasp.csv').open() as f:rows=list(csv.DictReader(f))
    models=['A','B','C','D','reference']
    sources=['old_candidate_'+str(i) for i in list(range(18))+[20,21,22,23]]+['new_1','new_16','new_29']
    fig,axes=plt.subplots(3,1,figsize=(13,7.5),sharex=True,layout='constrained')
    for ax,protocol,title in zip(axes,['fixed2','fixed5','arrival'],['Strict: fixed 2 s','Strict: fixed 5 s','Loose: arrival-triggered, at least 3 cycles']):
        values=np.array([[float(next(r['success_rate'] for r in rows if r['model']==m and r['protocol']==protocol and r['source_id']==s)) for s in sources] for m in models])
        im=ax.imshow(values,aspect='auto',vmin=0,vmax=1,cmap='viridis');ax.set_yticks(range(5),models);ax.set_title(title,loc='left')
        for boundary in [2.5,15.5,21.5]:ax.axvline(boundary,color='white',linewidth=1)
    axes[-1].set_xticks(range(25),[s.replace('old_candidate_','O').replace('new_','N') for s in sources],rotation=45)
    axes[-1].set_xlabel('Base grasps: O0–2 original; O3–15 additional train; O16–23 historical; N1/16/29 amended physical supplement')
    fig.colorbar(im,ax=axes,label='Success fraction (32 perturbations per base)',shrink=.8)
    fig.suptitle('Wuji matched 163,840,000 interactions per arm — one training seed; all trials shown')
    fig.savefig(a.analysis/'per-base-outcomes.png',dpi=160)
    fig.savefig(a.analysis/'per-base-outcomes.pdf')
if __name__=='__main__':main()
