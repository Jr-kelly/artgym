"""Render actual collision triangles, measured annotations; no private photos."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import ConvexHull
from scripts.g2_knife_geometry import KnifeGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();g=KnifeGeometry(a.spec)
 fig=plt.figure(figsize=(13,7));ax=fig.add_subplot(121,projection='3d');side=fig.add_subplot(222);front=fig.add_subplot(224)
 for part in g.collision_parts(0):
  v=part['vertices']*1000;color='#275e80' if part['link']=='link_1' else '#a8aeb5';h=ConvexHull(v)
  ax.add_collection3d(Poly3DCollection([v[f][:,[2,0,1]] for f in h.simplices],alpha=.85,facecolor=color,edgecolor='#444444',linewidth=.15))
  for sub,cols in [(side,[2,1]),(front,[2,0])]:
   points=v[:,cols];h2=ConvexHull(points);poly=points[h2.vertices];sub.fill(poly[:,0],poly[:,1],color=color,alpha=.85,edgecolor='#444444',linewidth=.6)
 ax.set(xlim=(-75,75),ylim=(-12,12),zlim=(-5,7),xlabel='Axis +z toward tip (mm)',ylabel='Width x (mm)',zlabel='Normal y (mm)');ax.set_box_aspect((150,24,12));ax.view_init(25,-65)
 for sub,title in [(side,'Side: body 8mm (derived), total10mm'),(front,'Top: body144x19mm; cap32x7mm')]:sub.set_aspect('equal');sub.set_title(title);sub.set_xlim(-76,76);sub.grid(alpha=.2);sub.set_xlabel('z from body center (mm); tail=-72mm')
 front.annotate('Initial cap center:46mm from tail',xy=(-26,0),xytext=(-50,23),arrowprops=dict(arrowstyle='->'),fontsize=9)
 fig.suptitle('New knife / actual URDF collision components\n55g total; q=0 is task initial, rail assumption[-10,+55]mm',fontsize=14)
 fig.text(.03,.02,'Blue: moving cap + internal blade carrier. Grey: floor, rails and rear support.\nRail/floor/chamfer/carrier shapes and 80/20 mass split are engineering assumptions; dimensions are user supplied.',fontsize=10)
 a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=160);plt.close(fig)
if __name__=='__main__':main()
