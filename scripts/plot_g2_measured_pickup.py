"""Plot actual measured-asset pickup failure; contact presence is not load."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();t=np.load(a.trace);time=t['time']
    fig,axes=plt.subplots(3,1,figsize=(10,7),sharex=True)
    settled=np.flatnonzero(t['phase']=='table_settle')[-1]
    axes[0].plot(time,(t['object'][:,2]-t['object'][settled,2])*1000)
    axes[0].set_ylabel('Body centre rise (mm)')
    axes[0].set_title('Measured-envelope knife: continuous table pickup attempt F1-08')
    contact=np.c_[t['finger_knife_contacts']>0,t['knife_table_contacts']>0]
    axes[1].imshow(contact.T,origin='upper',aspect='auto',interpolation='nearest',extent=[0,time[-1],5.5,-.5],cmap='Blues',vmin=0,vmax=1)
    axes[1].set_yticks(range(6));axes[1].set_yticklabels(['Thumb','Index','Middle','Ring','Pinky','Knife/table'])
    axes[1].set_ylabel('Contact present (not load)')
    axes[2].plot(time,(t['slider']-t['slider'][settled])*1000,color='#a65015')
    axes[2].set_ylabel('Passive slider change (mm)');axes[2].set_xlabel('Actual execution time (s)')
    for ax in axes:
        for phase in ['approach','close','lift','pickup_hold']:
            ix=np.flatnonzero(t['phase']==phase)
            if len(ix):ax.axvline(time[ix[0]],color='gray',lw=.6,ls='--')
        ax.grid(axis='x',alpha=.2)
    axes[0].text(.01,.97,'No complete table separation; no flip or policy execution',transform=axes[0].transAxes,va='top')
    fig.tight_layout();fig.savefig(a.output,dpi=160)


if __name__=='__main__':main()
