"""Two unobstructed views of actual recorded collision geometry and native contacts."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform

def plot(trial,output,clocks,knife_spec=None):
    z=np.load(trial/'trace.npz');g=DigitGeometry(knife_spec=knife_spec or trial/'evaluated-geometry.json')
    colors=dict(index='#4082c4',middle='#ddad36',thumb='#d5584c',ring='#65a174',pinky='#9266aa')
    fig=plt.figure(figsize=(4*len(clocks),8))
    for col,t in enumerate(clocks):
        elapsed=z['time']-z['time'][0]+1/30;i=int(np.argmin(abs(elapsed-t)));q=z['q'][i];frames=g.w.forward(q);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);O=transform(z['object'][i,:3],z['object'][i,3:7]);K=np.linalg.inv(W)@O
        for row,az in enumerate([-65,115]):
            ax=fig.add_subplot(2,len(clocks),row*len(clocks)+col+1,projection='3d')
            for name,parts in g.meshes.items():
                f=next((f for f in colors if '_'+f+'_' in name),None);X=frames[name]
                for v,_ in parts:
                    v=(v@X[:3,:3].T+X[:3,3])*1000;h=ConvexHull(v)
                    ax.add_collection3d(Poly3DCollection(v[h.simplices],facecolors=colors.get(f,'#bbbbbb'),alpha=.65,edgecolors='#333333',linewidths=.05))
            for part in g.knife_geometry.collision_parts(float(z['slider'][i])):
                v=(part['vertices']@K[:3,:3].T+K[:3,3])*1000;h=ConvexHull(v)
                ax.add_collection3d(Poly3DCollection(v[h.simplices],facecolors='#151515' if part['link']=='link_1' else '#7b838d',alpha=.75,edgecolors='black',linewidths=.15))
            ax.set_xlim(-85,125);ax.set_ylim(-100,85);ax.set_zlim(-50,140);ax.set_box_aspect((210,185,190));ax.view_init(20,az);ax.set_title('Actual elapsed %.2fs / azimuth %d'%(elapsed[i],az));ax.set_xlabel('Wrist X mm');ax.set_ylabel('Wrist Y mm');ax.set_zlabel('Wrist Z mm')
    fig.suptitle('Actual recorded collision hulls; blue index, yellow middle, red thumb, green ring, purple pinky\nTwo views of identical physical states; geometry reconstruction, not a new simulation/video.',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output,dpi=130);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--elapsed',type=float,nargs='+',required=True);p.add_argument('--knife-spec',type=Path);a=p.parse_args();plot(a.trial,a.output,a.elapsed,a.knife_spec)
