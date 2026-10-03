"""Plot closed development evidence; never read independent heldouts."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];d=root/'research/robust-knife-family-20261003'
    folder=root/'runs/robust-knife-family-20261003/checks/P50-lift8-reward-transition-v56'
    rows=[json.loads(x) for x in (folder/'episodes.jsonl').read_text().splitlines()];assert len(rows)==512
    groups={'Complete':('#277b48',[]),'Pickup/hold':('#d69b20',[]),'Body unstable/drop':('#c04c4a',[]),'Other':('#546cb0',[])}
    for row in rows:
        params=json.loads((root/'assets/objects/knife_wuji_dense_under_20261003'/row['instance']/'parameters.json').read_text());w,t,_=np.array(params['handle_size'])*1000
        label='Complete' if row['operation_complete'] else 'Pickup/hold' if row['failure']=='pickup/hold' else 'Body unstable/drop' if row['failure']=='body unstable/drop' else 'Other';groups[label][1].append((t,w))
    result=json.loads((d/'joint-failure-component-diagnostic-v1.json').read_text())['results']
    names=['baseline','calibration','placement','sensor','latency','material'];labels=['All joint\nconditions','No calibration\nerror','No placement\nerror','No sensor\nperturbation','No one-step\nlatency','Fixed\nmaterials']
    fig,axes=plt.subplots(1,2,figsize=(13,5.7),gridspec_kw={'width_ratios':[1,1.45]})
    for label,(color,points) in groups.items():
        if points:
            values=np.array(points);axes[0].scatter(values[:,0],values[:,1],s=15,c=color,label=f'{label} ({len(points)})',alpha=.8,edgecolors='none')
    axes[0].scatter([12],[16],marker='*',s=130,c='black',label='Nominal body reference',zorder=5)
    axes[0].set(xlabel='Body thickness [mm; excludes slider]',ylabel='Body width [mm]',title='Actual 512 joint development episodes',xlim=(9.9,14.1),ylim=(13.9,18.1));axes[0].legend(fontsize=8,loc='lower left',framealpha=.94)
    x=np.arange(len(names));width=.36
    for offset,key,nkey,color,label in [(-width/2,'complete','n','#426ca8','All 512'),(width/2,'top_thickness_complete','top_thickness_n','#c45e55','Predefined thick 128')]:
        values=[100*result[name][key]/result[name][nkey] for name in names];bars=axes[1].bar(x+offset,values,width,color=color,label=label)
        for bar,name in zip(bars,names):axes[1].text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,f"{result[name][key]}/{result[name][nkey]}",ha='center',va='bottom',fontsize=8,rotation=90)
    axes[1].set_xticks(x,labels,fontsize=8);axes[1].set(ylabel='Complete actual workflow [%]',ylim=(0,100),title='Finite leave-one-out contributor diagnostics');axes[1].legend(fontsize=9,loc='upper right')
    for axis in axes:axis.grid(alpha=.18);axis.set_axisbelow(True)
    fig.suptitle('Fixed P50 policy at 8s takeover: joint grip/operation fragility remains',fontsize=13)
    fig.text(.03,.025,'Development only. Other geometry/slider/load/contact/observation conditions co-vary. No independent heldouts or real robot results.\nRemaining initial fields match exactly; PhysX contact repeats can still differ. Counts do not establish an isolated thickness cause or small-rate learning gain.',fontsize=8)
    fig.tight_layout(rect=(0,.11,1,.95));a.output.mkdir(parents=True,exist_ok=True);fig.savefig(a.output/'joint-development.png',dpi=170);fig.savefig(a.output/'joint-development.pdf');plt.close(fig)
    (a.output/'sources.json').write_text(json.dumps(dict(policy='P50',takeover_seconds=8,evidence=str(folder.relative_to(root)),contributor_evidence='research/robust-knife-family-20261003/joint-failure-component-diagnostic-v1.json',scope='Closed development visualization; actor does not receive plotted geometry or outcomes'),indent=2))


if __name__=='__main__':main()
