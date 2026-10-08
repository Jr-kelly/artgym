"""Closest point on triangles of an unchanged original convex collision hull."""
import numpy as np
from scipy.spatial import ConvexHull

class OriginalContactSurface:
 def __init__(self,vertices):
  v=np.asarray(vertices,dtype=float);self.hull=ConvexHull(v);self.triangles=v[self.hull.simplices]
 def project(self,point):
  t=self.triangles;a=t[:,0];ab=t[:,1]-a;ac=t[:,2]-a;p=np.asarray(point,dtype=float);ap=p-a;d00=np.sum(ab*ab,1);d01=np.sum(ab*ac,1);d11=np.sum(ac*ac,1);d20=np.sum(ap*ab,1);d21=np.sum(ap*ac,1);den=d00*d11-d01*d01;b=(d11*d20-d01*d21)/den;c=(d00*d21-d01*d20)/den;inside=(b>=0)&(c>=0)&(b+c<=1);plane=a+b[:,None]*ab+c[:,None]*ac;best=plane.copy();dist=np.sum((best-p)**2,1);dist[~inside]=np.inf
  for i,j in[(0,1),(1,2),(2,0)]:
   start=t[:,i];edge=t[:,j]-start;u=np.clip(np.sum((p-start)*edge,1)/np.sum(edge*edge,1),0,1);q=start+u[:,None]*edge;d=np.sum((q-p)**2,1);use=d<dist;best[use]=q[use];dist[use]=d[use]
  return best[int(np.argmin(dist))].copy()
