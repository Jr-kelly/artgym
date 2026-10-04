"""Original collision hulls reconstructed from recorded physical joint/pose states.

Contact points and arrows come from the matching solver normal records. This
is evaluation, not a new rollout, contact area, full contact wrench, or material
calibration. Observed joint noise is never used for this reconstruction.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Patch
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform


def display(v): return np.asarray(v)[..., [2, 0, 1]]*1000


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    g=DigitGeometry(knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json')
    colors=dict(thumb='#d45b3d',index='#3c7fbd',middle='#c4a235',pinky='#8f6bb1',ring='#8e9299')
    cases=[('Original source2',Path('runs/wrap-force-20261004/comparison/source2-original-pressure080-v3')),
           ('Index under-wrap',Path('runs/wrap-force-20261004/comparison/index-wrap-v8-pressure080-v3'))]
    clocks=[14.5,20.8,25.8,30.8,35.8]; fig=plt.figure(figsize=(22,13)); evidence=[]
    grid=fig.add_gridspec(4,5,height_ratios=[4,1.2,4,1.2],hspace=.16,wspace=.12)
    for row,(label,path) in enumerate(cases):
        tr=np.load(path/'trace.npz'); contacts=[json.loads(s) for s in (path/'wrap-contact-physical-steps.jsonl').open()]
        ct=np.array([r['time_s'] for r in contacts])
        for col,clock in enumerate(clocks):
            i=int(np.argmin(abs(tr['time']-clock))); r=contacts[int(np.argmin(abs(ct-tr['time'][i])))]; actual=float(tr['time'][i])
            wrist=np.linalg.inv(transform(tr['object'][i,:3],tr['object'][i,3:7]))@transform(tr['wrist'][i,:3],tr['wrist'][i,3:7])
            frames=g.w.forward(tr['q'][i]); ax=fig.add_subplot(grid[row*2,col],projection='3d')
            for name,meshes in g.meshes.items():
                if not name.endswith(('pad_link','link4','base_link')):continue
                finger=next((f for f in colors if '_'+f+'_' in name),None)
                color=colors.get(finger,'#7a8490'); mat=wrist@frames[name]
                for vertices,_ in meshes:
                    v=vertices@mat[:3,:3].T+mat[:3,3]; hull=ConvexHull(v)
                    ax.add_collection3d(Poly3DCollection(display(v[hull.simplices]),facecolors=color,edgecolors='none',alpha=.20))
            for part in g.knife_geometry.collision_parts(float(tr['slider'][i])):
                v=part['vertices']; hull=ConvexHull(v)
                ax.add_collection3d(Poly3DCollection(display(v[hull.simplices]),facecolors='#53565c' if part['link']=='link_0' else '#121b25',edgecolors='#555555',linewidths=.2,alpha=.35))
            groups={}
            for c in r['contacts']:
                key=(c['hand_link'],c['knife_link']); groups.setdefault(key,[]).append(c)
            labels=[]
            for (link,knife),cs in groups.items():
                weights=np.array([c['normal_magnitude_N'] for c in cs]); total=float(weights.sum())
                point=np.average([c['position_knife_m'] for c in cs],weights=weights,axis=0)
                force=np.sum([c['force_normal_contribution_knife_N'] for c in cs],axis=0)
                xyz=display(point); arrow=display(force*.008)
                ax.scatter(*xyz,color='black',s=12); ax.quiver(*xyz,*arrow,color='black',linewidth=.9,arrow_length_ratio=.22)
                text=link.replace('hand_r_','').replace('_pad_link',' pad').replace('_link4',' joint4')
                labels.append(text+' %.2fN'%total)
            ax.view_init(elev=20,azim=-65); ax.set_xlim(-95,95);ax.set_ylim(-35,35);ax.set_zlim(-25,115)
            ax.set_box_aspect((190,70,140));ax.set_xlabel('Axial mm',fontsize=7);ax.set_ylabel('Width mm',fontsize=7);ax.set_zlabel('Normal mm',fontsize=7);ax.tick_params(labelsize=6)
            ax.set_title(label+'\nt=%.1fs'%actual,fontsize=10)
            text_ax=fig.add_subplot(grid[row*2+1,col]);text_ax.axis('off')
            text_ax.text(.03,.95,'\n'.join(labels),va='top',fontsize=9,transform=text_ax.transAxes)
            evidence.append(dict(trial=str(path),time_s=actual,contact_time_s=r['time_s'],
                relative_wrist_in_knife=wrist.tolist(),physical_q=tr['q'][i].tolist(),contacts=r['contacts']))
    fig.suptitle('Paired held diagnostics: original pad / distal-joint / palm collision geometry and actual normal contacts\n'
        'Physical q and wrist/body poses are recorded truth for evaluation only. Normal arrows:8mm/N; no total axial force or real contact-area claim.',fontsize=12)
    fig.legend(handles=[Patch(color=c,alpha=.5,label=f) for f,c in colors.items()],loc='lower center',ncol=5)
    fig.subplots_adjust(top=.89,bottom=.07)
    for suffix in ['png','pdf','svg']:fig.savefig(a.output/('recorded-wrap-geometry.'+suffix),dpi=150,bbox_inches='tight')
    plt.close(fig)
    result=dict(scope=__doc__,points=evidence,provenance=[dict(trial=str(path),
        trace_sha256=hashlib.sha256((path/'trace.npz').read_bytes()).hexdigest(),
        contact_sha256=hashlib.sha256((path/'wrap-contact-physical-steps.jsonl').read_bytes()).hexdigest()) for _,path in cases])
    (a.output/'recorded-points.json').write_text(json.dumps(result,indent=2)+'\n');print(a.output)


if __name__=='__main__':main()
