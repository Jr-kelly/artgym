"""Plot measured learning reward and separate deterministic task metrics."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read_lines(path):
    result=[]
    if path.exists():
        for line in path.read_text().splitlines():
            try:result.append(json.loads(line))
            except json.JSONDecodeError:pass  # active writer may have a partial final line
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    fig, axes=plt.subplots(2,2,figsize=(11,7))
    offset=0
    for folder in a.runs:
        rows=read_lines(folder/'learning.jsonl')
        if not rows:continue
        x=np.array([r['transitions'] for r in rows])+offset
        axes[0,0].plot(x,[r['reward'] for r in rows],label=folder.name)
        axes[0,1].plot(x,[r['end_to_end_transitions_per_second'] for r in rows],label=folder.name)
        ex, success, rot, drift=[],[],[],[]
        by_update={r['update']:r for r in rows}
        for f in sorted(folder.glob('eval-*.json')):
            r=json.loads(f.read_text());m=r['metrics'];row=by_update.get(r['update'])
            if row is None:continue
            ex.append(offset+row['transitions']);success.append(np.mean(m['success']))
            rot.append(np.median(m['world_rotation_rad']));drift.append(np.median(m['world_drift_m'])*1000)
        axes[1,0].plot(ex,success,'o-',label=folder.name)
        axes[1,1].plot(ex,rot,'o-',label=folder.name)
        offset=int(x[-1])
    titles=['Training reward (not success)','End-to-end throughput incl. evaluation','Development H/S success (same source replicas)','Median episode maximum rotation']
    units=['mean reward','transitions / wall second','fraction','rad']
    for ax,title,unit in zip(axes.flat,titles,units):
        ax.set_title(title);ax.set_xlabel('sampled training transitions');ax.set_ylabel(unit);ax.grid(alpha=.25)
    axes[1,0].set_ylim(-.02,1.02)
    axes[1,1].axhline(.25,color='red',ls='--',label='fixed .25rad criterion')
    axes[0,0].legend(fontsize=7)
    axes[1,1].legend(fontsize=7)
    fig.tight_layout()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.output,dpi=150)


if __name__=='__main__':main()
