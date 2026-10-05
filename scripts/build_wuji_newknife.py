"""Measured new-knife envelope and explicitly assumed contact/inner geometry.
Coordinates x=width,y=outward slider normal,z=tail-to-tip, body origin=center.
No external modeling service, private image, force measurement, or hardware call.
"""
import argparse,json,hashlib,itertools,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull

def build(out,length=.144,width=.019,thickness=.008,slider_length=.032,slider_width=.007,protrusion=.002,proximal=.030,mass=.055):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 robot=E.Element('robot',name='wuji_newknife_20261005');components={}
 def link(name,m,size):
  l=E.SubElement(robot,'link',name=name);components[name]=[];i=E.SubElement(l,'inertial');E.SubElement(i,'mass',value=str(m));x,y,z=size
  E.SubElement(i,'inertia',ixx=str(m*(y*y+z*z)/12),iyy=str(m*(x*x+z*z)/12),izz=str(m*(x*x+y*y)/12),ixy='0',ixz='0',iyz='0');return l
 def part(l,size,origin,color,mesh=None):
  if size is not None:components[l.get('name')].append((float(np.prod(size)),np.asarray(origin),np.asarray(size)))
  for tag in ['visual','collision']:
   q=E.SubElement(l,tag);E.SubElement(q,'origin',xyz=' '.join(map(str,origin)));g=E.SubElement(q,'geometry')
   if mesh:E.SubElement(g,'mesh',filename=mesh)
   else:E.SubElement(g,'box',size=' '.join(map(str,size)))
   if tag=='visual':E.SubElement(E.SubElement(q,'material',name=l.get('name')+str(len(l))), 'color',rgba=color)
 body=link('link_0',mass*.8,[width,thickness,length]);slider=link('link_1',mass*.2,[slider_width,.003,slider_length])
 # First box is the measured outer envelope for legacy metadata readers. Its
 # actual thickness is lower floor; separate rails preserve the open trough.
 floor=.002;rail=.0025
 part(body,[width,floor,length],[0,-thickness/2+floor/2,0],'.25 .27 .30 1')
 for side in [-1,1]:part(body,[rail,thickness-floor,length],[side*(width-rail)/2,floor/2,0],'.62 .65 .69 1')
 # Rear support cap; open track remains hollow beyond initial slider proximal edge.
 part(body,[width-2*rail,thickness-floor,proximal-.002],[0,floor/2,-length/2+(proximal-.002)/2],'.10 .11 .13 1')
 # Chamfered effective contact cap: measured maximum width, length and height.
 points=[];ch=min(.0005,protrusion/3)
 for y,w,l in [(-protrusion/2,slider_width,slider_length),(protrusion/2-ch,slider_width,slider_length),(protrusion/2,slider_width-2*ch,slider_length-2*ch)]:
  points += [[x,y,z] for x in [-w/2,w/2] for z in [-l/2,l/2]]
 v=np.array(points);h=ConvexHull(v);faces=[]
 for face,eq in zip(h.simplices,h.equations):
  f=face.copy()
  if np.dot(np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]),eq[:3])<0:f=f[::-1]
  faces.append(f)
 (out/'slider-cap.obj').write_text('\n'.join(['v '+' '.join(map(str,p)) for p in v]+['f '+' '.join(str(i+1) for i in f) for f in faces])+'\n')
 tetra=[]
 for face in h.simplices:
  verts=v[face];volume=abs(np.linalg.det(verts))/6;tetra.append((volume,verts.sum(axis=0)/4))
 capvolume=sum(x[0] for x in tetra);capcenter=sum(vol*c for vol,c in tetra)/capvolume
 components['link_1'].append((capvolume,capcenter,np.array([slider_width,protrusion,slider_length])))
 part(slider,None,[0,0,0],'.12 .13 .15 1','slider-cap.obj')
 # Internal blade carrier is below cap, moves with it; thickness/mass are assumptions.
 part(slider,[.011,.0005,.075],[0,-protrusion/2-.0015,.022],'.65 .68 .70 1')
 origin=[0,thickness/2+protrusion/2,-length/2+proximal+slider_length/2]
 j=E.SubElement(robot,'joint',name='slider',type='prismatic');E.SubElement(j,'parent',link='link_0');E.SubElement(j,'child',link='link_1');E.SubElement(j,'origin',xyz=' '.join(map(str,origin)));E.SubElement(j,'axis',xyz='0 0 1');E.SubElement(j,'limit',lower='-.010',upper='.055',effort='100',velocity='1');E.SubElement(j,'dynamics',damping='0',friction='0')
 centers={}
 for node in [body,slider]:
  rows=components[node.get('name')];total=sum(x[0] for x in rows);center=sum(vol*c for vol,c,_ in rows)/total;centers[node.get('name')]=center.tolist();inertial=node.find('inertial');E.SubElement(inertial,'origin',xyz=' '.join(map(str,center)),rpy='0 0 0')
  m=float(inertial.find('mass').get('value'));tensor=np.zeros((3,3))
  for vol,c,size in rows:
   piece=m*vol/total;d=c-center;xx,yy,zz=size;tensor+=np.diag([piece*(yy*yy+zz*zz)/12,piece*(xx*xx+zz*zz)/12,piece*(xx*xx+yy*yy)/12])+piece*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
  n=inertial.find('inertia')
  for key,i,j in [('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]:n.set(key,str(tensor[i,j]))
 E.ElementTree(robot).write(out/'mobility.urdf',encoding='utf-8',xml_declaration=True)
 params=dict(handle_size=[width,thickness,length],slider_size=[slider_width,protrusion,slider_length],initial_slider_q_m=0.,total_mass_kg=mass,estimated_com_local_m=centers,body_mass_kg=.8*mass,moving_mass_kg=.2*mass,slider_initial_center_tail_m=proximal+slider_length/2,slider_origin_m=origin,task_command_m=.035,assumptions=dict(body_thickness=('Derived nominal total10mm minus protrusion2mm' if abs(thickness-.008)<1e-9 and abs(protrusion-.002)<1e-9 else 'Explicit nearby synthetic body thickness; not a second measured knife'),mass_split='80/20 percent engineering estimate; uniform-volume part COM, compound-box inertia approximation',collision='2mm floor,2.5mm side rails,rear cap,0.5mm chamfer and internal blade carrier are photo-informed engineering assumptions',joint_limits='-10 to55mm relative initial; unmeasured, targets not endstops'),model_route='Parameterized URDF; no existing Hunyuan workflow found, simple measured contact geometry more direct')
 (out/'parameters.json').write_text(json.dumps(params,indent=2));spec=dict(asset_urdf=str(out/'mobility.urdf'),file_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()},planning=dict(side_half_width_m=width/2,side_contact_y_interval_m=[-thickness/3,thickness/3]),initial_slider_q_m=0.)
 (out/'spec.json').write_text(json.dumps(spec,indent=2))
 estimate=dict(source='Synthetic initial dimensional observation centered at user supplied values; uncertainty is assumed, not sensor calibration',uncertainty_m=.0003,handle_size_WTL_m=[width,thickness,length],slider_size_WTL_m=[slider_width,protrusion,slider_length],slider_contact_shift_m=[0,protrusion-.003,origin[2]-(-.02205)],initial_slider_q_m=0.,newknife_contact_geometry=True)
 (out/'once-estimate.json').write_text(json.dumps(estimate,indent=2));return params
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.output),indent=2))
