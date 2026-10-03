"""Standalone force/travel/stability figures from actual native demo traces."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(4,len(a.episode),figsize=(7*len(a.episode),10),squeeze=False,sharex='col')
    metadata=[]
    for col,path in enumerate(a.episode):
        z=np.load(path/'trace.npz');report=json.loads((path/'report.json').read_text());t=z['time'];mask=t>=12;reference=z['object'][np.argmin(abs(t-16))]
        rotation=Rotation.from_quat(reference[3:7]).inv()*Rotation.from_quat(z['object'][:,3:7])
        pressure=z['pair_slider_pressure_mean_N'][:,0];low=z['pair_slider_pressure_min_N'][:,0];high=z['pair_slider_pressure_max_N'][:,0]
        axes[0,col].plot(t[mask],pressure[mask],label='Thumb-slider normal: measured pairs',color='#2367aa')
        axes[0,col].fill_between(t[mask],low[mask],high[mask],color='#2367aa',alpha=.12,label='Min/max of 8 physical steps')
        estimate=z['estimated_thumb_pressure_N']
        if np.isfinite(estimate).any():axes[0,col].plot(t[mask],estimate[mask],color='#b66a24',alpha=.8,label='Joint-deflection model estimate')
        axes[0,col].set_ylabel('Pressure (N)');axes[0,col].legend(fontsize=8);axes[0,col].set_title(path.name+'\n'+('Full continuous success' if report['full_success'] else 'Failure: '+report['first_failure']))
        order=['thumb','index','middle','ring','pinky']
        for i in [1,2,3,4]:axes[1,col].plot(t[mask],z['pair_underside_support_mean_N'][mask,i],label=order[i],lw=1)
        axes[1,col].set_ylabel('Underside normal reaction (N)');axes[1,col].legend(fontsize=8,ncol=4)
        command_clock=t-1/30;goal=np.where((command_clock>=16-1e-7)&(((np.maximum(command_clock-16+1e-7,0)//5).astype(int)%2)==0),40,0)
        axes[2,col].plot(t[mask],(z['slider'][mask]-z['slider'][0])*1000,label='Actual rail travel',color='#297d51');axes[2,col].step(t[mask],goal[mask],where='post',label='Issued external goal',color='#777777',ls='--');axes[2,col].set_ylabel('Travel (mm)');axes[2,col].legend(fontsize=8)
        operation=t>=16;axes[3,col].plot(t[operation],rotation.magnitude()[operation],color='#b34444',label='Body rotation relative to handover');axes[3,col].axhline(.25,color='#222222',ls='--',label='Original .25 rad criterion');axes[3,col].set_ylabel('Body rotation (rad)');axes[3,col].set_xlabel('Continuous episode time (s)');axes[3,col].legend(fontsize=8)
        for row in range(4):
            ax=axes[row,col];ax.axvspan(12,16,color='#888888',alpha=.06);ax.set_xlim(12,36);ax.grid(alpha=.15)
        metadata.append({'episode':str(path),'report':'report.json','physical_hz':240,'sample_mean_steps':8,'full_success':report['full_success'],'force_scope':'Native contact pair normal contributions only; tangential friction not reconstructed; no online control truth input'})
    fig.tight_layout()
    for ext in ['png','svg','pdf']:fig.savefig(a.output/('pressure-travel-stability.'+ext),dpi=160)
    plt.close(fig);(a.output/'figure.json').write_text(json.dumps(metadata,indent=2))
if __name__=='__main__':main()
