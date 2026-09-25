"""Plot measured rollout traces; successful and regressed learned checkpoints."""
import json,shutil,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/wuji-goal/release-20260922-0120'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    for ax,name,label in zip(axes,['precision-ft-cp10-trace100','precision-ft-cp100-regression-trace100'],
        ['Teacher CP10: successful open-close','Teacher CP100: opening dwell not achieved']):
        folder=ROOT/'runs/wuji-goal/verification'/name
        trace=np.load(folder/'trace.npz');report=json.loads((folder/'report.json').read_text())
        active=trace['active'][:,0].astype(bool);t=(np.arange(len(active))+1)*report['control_dt']
        goal=trace['goal'][:,0]*1000;slider=trace['slider'][:,0]*1000
        ax.fill_between(t[active],goal[active]-2,goal[active]+2,color='#c9dfef',alpha=.6,label='Goal tolerance: +/-2 mm')
        ax.step(t[active],goal[active],where='post',color='#73818c',linestyle='--',label='Goal')
        ax.plot(t[active],slider[active],color='#007d79' if 'cp10-' in name else '#d36636',lw=1.6,label='Measured slider')
        for event in np.flatnonzero(trace['stage_event'][:,0]*active):
            ax.axvline(t[event],color='#31874f',alpha=.4,lw=.8)
        ax.set_title(label,loc='left',fontsize=12);ax.set_ylabel('Slider position (mm)')
        ax.grid(alpha=.18);ax.set_ylim(-3,47);ax.set_xlim(0,10)
    axes[0].legend(loc='center right',fontsize=9);axes[1].set_xlabel('Simulated time (s)')
    fig.savefig(OUT/'wuji-knife-rl-precision-cp10-vs-cp100-dwell-20260922.png',dpi=180);plt.close(fig)
    video_dir=ROOT/'runs/wuji-goal/verification/precision-ft-cp10-local-video'
    report=json.loads((video_dir/'report.json').read_text())
    if report['successful_trials']!=1 or report['strict_first_cycle_trials']!=1:
        raise ValueError('The video rollout did not pass its independent physical checks')
    name='wuji-knife-rl-precision-cp10-2mm-300ms-20260922'
    shutil.copy2(video_dir/'policy.mp4',OUT/(name+'-no-text.mp4'))
    reader=imageio.get_reader(video_dir/'policy.mp4');frame=reader.get_data(60);reader.close()
    imageio.imwrite(OUT/(name+'-poster.png'),frame)
    files=sorted(p for p in OUT.iterdir() if p.suffix in ['.png','.mp4'])
    (OUT/(name+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    print(json.dumps({'files':[p.name for p in files],'local_video_cycles':report['records'][0]['cycles']}))


if __name__=='__main__':main()
