"""Actual convex facet clipped to object contact rectangle; no invented contact points or area."""
import numpy as np

def clip_polygon(poly,axis,value,keep_above):
 out=[]
 for i,a in enumerate(poly):
  b=poly[(i+1)%len(poly)];da=(a[axis]-value)*(1 if keep_above else -1);db=(b[axis]-value)*(1 if keep_above else -1)
  if da>=-1e-12:out.append(a)
  if (da>=0)!=(db>=0):out.append(a+(b-a)*da/(da-db))
 return np.array(out)

def surface_region(points,triangles,normals,normal,lower,upper,facing_min=.5):
 axis=int(np.argmax(abs(normal)));side=[i for i in range(3) if i!=axis];center=(lower+upper)/2;best=None
 for tri,n in zip(triangles,normals):
  poly=points[tri].copy()
  for j in side:
   poly=clip_polygon(poly,j,lower[j],True) if len(poly) else poly
   poly=clip_polygon(poly,j,upper[j],False) if len(poly) else poly
  if not len(poly):continue
  # Nearest true facet point to the contact plane, retaining the whole cross-region.
  proj=poly[:,axis]-center[axis]
  if proj.min()<=0<=proj.max():
   first=int(np.argmin(proj));last=int(np.argmax(proj));point=poly[first]+(poly[last]-poly[first])*(-proj[first])/(proj[last]-proj[first]+1e-30)
  elif np.ptp(proj)<1e-8:point=poly.mean(0)
  else:point=poly[int(np.argmin(abs(proj)))]
  facing=float(n@(-normal));distance=float(abs(point[axis]-center[axis]));score=distance+.02*max(0,facing_min-facing)
  if best is None or score<best[0]:best=(score,point,facing)
 return None if best is None else (best[1],best[2])
