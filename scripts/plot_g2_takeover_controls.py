"""Standalone evidence figure from actual traces; never modifies videos."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.diagnose_g2_takeover_controls import errors


def main():
    p=argparse.ArgumentParser();p.add_argument('--comparison',type=Path,required=True)
    p.add_argument('--run-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    data=json.loads(a.comparison.read_text());fig,axes=plt.subplots(3,2,figsize=(13,9),sharex=True)
    for row in data['trials']:
        trace=np.load(a.run_root/row['trial']/'trace.npz');ref=row['reference_frame']
        selection=np.arange(ref+1,ref+1+row['samples']);tm=trace['time'][selection]-trace['time'][ref]
        label=row['trial'].split('-candidate2')[0]+' '+row['action_mode']
        if '-A-' in row['trial']:label=row['trial'].split('-A-')[0]+' preset A'
        pos,rot=errors(trace['object'][selection],trace['object'][ref])
        values=[(trace['slider'][selection]-trace['slider'][ref])*1000,pos*1000,rot,
                trace['q'][selection,-1],trace['finger_slider_contacts'][selection,0]>0,
                (trace['finger_knife_contacts'][selection,1:]>0).sum(1)]
        for ax,y in zip(axes.flat,values):ax.plot(tm,y,label=label,lw=1.2)
    axes[0,0].plot([0,5,5,10,10,15,15,20],[40,40,0,0,40,40,0,0],'k--',lw=1,label='Policy command')
    axes[0,1].axhline(10,c='k',ls='--',lw=1)
    axes[1,0].axhline(.25,c='k',ls='--',lw=1)
    labels=['Slider travel from actual takeover [mm]','Fixed-world position error [mm]',
            'Fixed-world rotation error [rad]','Measured thumb joint 4 [rad]',
            'Thumb-slider effective contact [0/1]','Non-thumb fingers in effective contact']
    for ax,label in zip(axes.flat,labels):ax.set_ylabel(label);ax.grid(alpha=.25);ax.set_xlim(0,20)
    for ax in axes[-1]:ax.set_xlabel('Time since fixed comparison reference [s]')
    axes[0,0].legend(fontsize=8,loc='upper right')
    fig.suptitle('G2 / Wuji takeover controls: recorded physical execution, unchanged thresholds')
    fig.tight_layout();fig.savefig(a.output,dpi=180);plt.close(fig)


if __name__=='__main__':main()
