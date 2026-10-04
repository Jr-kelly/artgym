"""Paired actual held contact distribution, separate from continuous validation."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

def save(fig,out,name):
    for suffix in ['png','pdf','svg']:fig.savefig(out/(name+'.'+suffix),dpi=170,bbox_inches='tight')
    plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    base=Path('runs/wrap-force-20261004')
    cases=[('Original source2',base/'comparison/source2-original-pressure080-v3'),
           ('Index under-wrap',base/'comparison/index-wrap-v8-pressure080-v3')]
    colors=['#536c9d','#bb4d22'];fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    provenance=[]
    for color,(label,path) in zip(colors,cases):
        z=np.load(path/'trace.npz');clock=z['time'];mask=clock>=16
        evaluation=json.loads((path/'functional-evaluation.json').read_text())
        rail=(z['slider']+.03267458688196273)*1000
        wr=Rotation.from_quat(z['wrist'][:,3:7]);rel=wr.inv()*Rotation.from_quat(z['object'][:,3:7]);origin=np.flatnonzero(mask)[0]-1
        angle=(rel[origin].inv()*rel).magnitude()
        axes[0].plot(clock[mask],rail[mask],color=color,label=label)
        axes[1].plot(clock[mask],z['pair_slider_pressure_mean_N'][mask,0],color=color,label=label)
        axes[2].plot(clock[mask],angle[mask],color=color,label=label)
        provenance.append(dict(label=label,trial=str(path),trace_sha256=hashlib.sha256((path/'trace.npz').read_bytes()).hexdigest(),functional_evaluation=evaluation))
    axes[0].axhline(25,color='gray',ls='--',lw=.9,label='Extension endpoint criterion')
    axes[0].axhline(8,color='gray',ls=':',lw=.9,label='Return endpoint criterion')
    axes[0].set_ylabel('Rail position above lower stop (mm)')
    axes[1].set_ylabel('A: measured thumb normal (N)')
    axes[2].set_ylabel('Knife / wrist relative rotation (rad)');axes[2].set_xlabel('Simulation clock (s)')
    for ax in axes:
        for x in [21,26,31]:ax.axvline(x,color='#b3bac4',lw=.6)
        ax.grid(alpha=.2);ax.legend(loc='upper left',fontsize=8)
    fig.suptitle('Matched S120 + 0.8 pressure-proxy held diagnostics\nSame physical constraints; grip and full-stroke reference adapted together. No pickup claim.',fontsize=12)
    fig.tight_layout(rect=[0,0,1,.94]);save(fig,a.output,'paired-held-motion-pressure')
    phases=['initial_hold','extend1','return1','extend2','return2']
    links=['hand_r_index_link4','hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_pinky_pad_link','hand_r_ring_pad_link']
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,(label,path) in zip(axes,cases):
        rows=json.loads((path/'wrap-contact-analysis.json').read_text())['rows'];lookup={(r['link'],r['phase']):r for r in rows}
        force=np.array([[lookup.get((link,phase),{}).get('underside_normal_mean_N',0) for phase in phases] for link in links])
        im=ax.imshow(force,vmin=0,vmax=.45,cmap='YlGnBu',aspect='auto')
        for i,link in enumerate(links):
            for j,phase in enumerate(phases):
                r=lookup.get((link,phase),{});fraction=r.get('contact_fraction',0)
                ax.text(j,i,'%.2f N\n%.0f%%'%(force[i,j],fraction*100),ha='center',va='center',fontsize=8,color='white' if force[i,j]>.27 else 'black')
        ax.set_xticks(range(5));ax.set_xticklabels(['Hold','Ext1','Ret1','Ext2','Ret2'])
        ax.set_yticks(range(5));ax.set_yticklabels([s.replace('hand_r_','') for s in links],fontsize=9);ax.set_title(label)
    fig.colorbar(im,ax=axes.tolist(),label='Actual underside normal contribution mean (N)',shrink=.8)
    fig.suptitle('Actual per-link support: normal mean and contact fraction\nBoth layouts already contact index link4. Solver distribution is not real contact area.',fontsize=12)
    save(fig,a.output,'paired-held-actual-support')
    continuous=base/'continuous/index-wrap-v8-direct-corner-mass-corrected-v4'
    cases=[('Nominal new wrap',continuous)]
    cases.extend(('Heldout '+i,base/'validation'/('wrap-direct-corner-geometry'+i+'-v14')) for i in ['012','013','014','015'])
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for label,path in cases:
        z=np.load(path/'trace.npz');mask=z['time']>=16
        axes[0].plot(z['time'][mask],(z['slider'][mask]+.03267458688196273)*1000,label=label)
        axes[1].plot(z['time'][mask],z['pair_slider_pressure_mean_N'][mask,0],label=label)
        provenance.append(dict(label=label,trial=str(path),trace_sha256=hashlib.sha256((path/'trace.npz').read_bytes()).hexdigest()))
    axes[0].set_ylabel('Rail position above lower stop (mm)');axes[1].set_ylabel('A: measured thumb normal (N)');axes[1].set_xlabel('Simulation clock (s)')
    for ax in axes:ax.grid(alpha=.2);ax.legend(ncol=3,fontsize=8)
    fig.suptitle('Actual continuous corner pickup, same S120, common noisy initial-estimate geometry\nBase brake capacity 0.2 N with passive startup/groove variation; not measured resistance.',fontsize=12)
    fig.tight_layout(rect=[0,0,1,.94]);save(fig,a.output,'continuous-common-geometry')
    (a.output/'provenance.json').write_text(json.dumps(dict(scope=__doc__,sources=provenance),indent=2)+'\n')
    print(json.dumps(dict(output=str(a.output),sources=len(provenance))))

if __name__=='__main__':main()
