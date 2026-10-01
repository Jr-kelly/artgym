"""Controlled boxes and local contact IK, without policy-based grasp selection."""
import argparse,copy,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics,FINGERS
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.record_wuji_geometry_goal import R,D,record
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def meshes(hand):
 xml=ET.parse(R/hand.config['asset']);result={}
 for link in xml.findall('link'):
  parts=[]
  for col in link.findall('collision'):
   mesh=col.find('geometry/mesh')
   if mesh is None:continue
   p=(R/hand.config['asset']).parent/mesh.get('filename')
   v=np.array([np.fromstring(t[2:],sep=' ') for t in p.read_text().splitlines() if t.startswith('v ')])
   v*=np.fromstring(mesh.get('scale','1 1 1'),sep=' ')
   o=col.find('origin')
   if o is not None:v=Rotation.from_euler('xyz',np.fromstring(o.get('rpy','0 0 0'),sep=' ')).apply(v)+np.fromstring(o.get('xyz','0 0 0'),sep=' ')
   parts.append(v)
  if parts:result[link.get('name')]=np.concatenate(parts)
 return result
def penetration(hand,mesh,s,size,origin):
 frames=hand.forward(s[:20]);rot=Rotation.from_quat(s[43:47]);depth=0.
 for link,vs in mesh.items():
  if not any('_'+f+'_' in link for f in FINGERS):continue
  frame=frames[link];v=rot.inv().apply(vs@frame[:3,:3].T+frame[:3,3]-s[40:43])
  for center,half in [(np.zeros(3),size/2),(origin+[0,0,s[54]],np.array([.01,.003,.03])/2)]:
   sdf=np.max(abs(v-center)-half,axis=1);depth=max(depth,float(max(0,-sdf.min())))
 return depth
def adapt(hand,s,size,origin,base):
 q=s[:20].astype(float).copy();points,normals=hand.contacts(q);rot=Rotation.from_quat(s[43:47]);local=rot.inv().apply(points-s[40:43]);targets=local.copy()
 for i,f in enumerate(FINGERS):
  if f=='thumb':targets[i,1]+=(size[1]-base[1])/2
  else:
   axis=int(np.argmax(abs(local[i])-base/2))
   targets[i,axis]+=np.sign(local[i,axis])*(size[axis]-base[axis])/2
   targets[i,2]=np.clip(targets[i,2],-size[2]/2+.001,size[2]/2-.001)
 targets=rot.apply(targets)+s[40:43]
 errors=[]
 for i,f in enumerate(FINGERS):
  ids=[hand.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)]
  initial=q[ids].copy()
  def residual(values):
   z=q.copy();z[ids]=values;p,n=hand.contacts(z)
   return np.r_[(p[i]-targets[i])*100,(n[i]-normals[i])*.15,(values-initial)*.005]
  fit=least_squares(residual,np.clip(initial,hand.lower[ids]+1e-7,hand.upper[ids]-1e-7),bounds=(hand.lower[ids],hand.upper[ids]),max_nfev=60)
  q[ids]=fit.x;errors.append(float(np.linalg.norm(hand.contacts(q)[0][i]-targets[i])))
 out=s.copy();out[:20]=q;out[20:40]=np.clip(q+(s[20:40]-s[:20]),hand.lower,hand.upper)
 out[47:50]+=rot.apply([0,(size[1]-base[1])/2,0])
 frames=hand.forward(out[:20]);out[55:70]=np.concatenate([frames[n][:3,3] for n in hand.config['track_links']])
 return out,dict(contact_errors_m=errors,max_q_change_rad=float(max(abs(q-s[:20]))),max_target_change_rad=float(max(abs(out[20:40]-s[20:40]))))
def main():
 p=argparse.ArgumentParser();p.add_argument('--labels',nargs='*');a=p.parse_args()
 base_asset=R/'assets/objects/knife_wuji_bridge3_20260922';base_meta=json.loads((base_asset/'000/parameters.json').read_text());base=np.array(base_meta['handle_size']);origin0=np.array(base_meta['slider_origin'])
 hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32);mesh=meshes(hand)
 seeds=np.load(R/'research/multigrasp-20260928/data/candidates.npy')[:4]
 definitions=[('baseline',[1,1,1])]+[(axis+str(int(factor*100)),[factor if j==idx else 1 for j in range(3)]) for axis,idx in [('L',2),('W',0),('T',1)] for factor in [.8,.9,1.1,1.2]]
 assets={};grasps={};entries=[];seen=set()
 for label,factors in definitions:
  if a.labels and label not in a.labels:continue
  size=base*np.array(factors);origin=origin0.copy();origin[1]+=(size[1]-base[1])/2
  name='knife_wuji_geo_'+label+'_20261002';folder=R/'assets/objects'/name;folder.mkdir(parents=True,exist_ok=False);(folder/'000').mkdir()
  tree=ET.parse(base_asset/'000/mobility.urdf')
  for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):box.set('size',' '.join(map(str,size)))
  tree.find("./joint[@name='slider']/origin").set('xyz',' '.join(map(str,origin)))
  urdf=folder/'000/mobility.urdf'
  if label=='baseline':shutil.copy2(base_asset/'000/mobility.urdf',urdf)
  else:tree.write(urdf,encoding='utf-8',xml_declaration=True)
  meta=copy.deepcopy(base_meta);meta.update(round='geometry-generalization-20261002',label=label,handle_size=size.tolist(),slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),total_size_lwt=[size[2],size[0],size[1]+.003],urdf_sha256=sha(urdf),mass_inertia_mode='both fixed at baseline: controlled geometry diagnostic',length_anchor='handle center and slider longitudinal origin fixed',thickness_coupling='slider joint origin Y shifts by half thickness difference',axes='URDF W,T,L; policy transforms bbox to W,L,T')
  (folder/'000/parameters.json').write_text(json.dumps(meta,indent=2)+'\n');(folder/'lbx.json').write_text(json.dumps({'000':size.tolist()+meta['slider_size']})+'\n')
  config=R/'isaacgymenvs/cfg/object'/(name+'.yaml');config.write_text('defaults:\n  - knife_wuji_bridge3_20260922\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000']\n")
  adapted=[];reports=[]
  for source,s in enumerate(seeds):
   out,rep=(s.copy(),dict(contact_errors_m=[0]*5,max_q_change_rad=0,max_target_change_rad=0)) if label=='baseline' else adapt(hand,s,size,origin,base)
   rep.update(source=source,baseline_vertex_penetration_m=penetration(hand,mesh,s,base,origin0),new_vertex_penetration_m=penetration(hand,mesh,out,size,origin))
   adapted.append(out);reports.append(rep)
  directory=D/'data'/label;directory.mkdir(parents=True)
  np.save(directory/'adapted-seeds.npy',adapted)
  cache=R/'caches/initial_grasp/wuji'/name/'000'
  cache.mkdir(parents=True,exist_ok=True)
  shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/grasp_state_metadata.json',cache/'grasp_state_metadata.json')
  for split in ['train','test']:
   (cache/split).mkdir(parents=True);np.save(cache/split/'valid_grasps.npy',adapted)
  for split,n,seed in [('screen-attempts',32,2026100201),('confirm-attempts',96,2026100202),('confirm128-attempts',192,2026100203),('final-attempts',192,2026100204)]:
   chunks=[]
   for source,s in enumerate(adapted):
    rows=states_for_seed(np.asarray(s)[None],seed*100+source,hand,trials=n);chunks.append(rows)
    for row in rows:
     digest=hashlib.sha256(row.tobytes()).hexdigest();key=(label,digest);assert key not in seen;seen.add(key)
   dest=directory/(split+'.npy');np.save(dest,np.concatenate(chunks));entries.append(dict(label=label,split=split,attempts_per_source=n,path=str(dest.relative_to(R)),sha256=sha(dest),paired_perturbation_seed=seed,source_order=[0,1,2,3],final_access='static and policy evaluation only after candidate freeze' if split.startswith('final') else 'development or independent confirmation'))
  assets[label]=dict(effective_inertia=json.loads((D/'BASELINE_PHYSICS.json').read_text())['actual_inertia'] if (D/'BASELINE_PHYSICS.json').exists() else None,effective_inertia_basis='measured baseline actor, frozen inWujiGeometry with recompute=False',object=name,dimensions_mm_LWT=[float(size[2]*1000),float(size[0]*1000),float(size[1]*1000)],parameters=meta,files={str(p.relative_to(R)):sha(p) for p in list(folder.rglob('*'))+[config] if p.is_file()})
  grasps[label]=reports
 (D/'ASSETS.json').write_text(json.dumps(assets,indent=2)+'\n');(D/'GRASPS.json').write_text(json.dumps(grasps,indent=2)+'\n');(D/'DATA.json').write_text(json.dumps(dict(entries=entries,unique_rows=len(seen),rule='first16 statically valid/source for screen, first64 for confirmation; never filter policy results; pairing lineage retained across geometry',old_final_use='none; new seeds/initial states; no historical final access',splits_seed_rule='seed*100+source; same perturbations across geometry',perturbations='joint ±.01rad, translation ±.5mm/axis, rotvec ±.5deg/axis',scope='conditional manipulation in three existing grasp clusters; adaptation coverage reported separately'),indent=2)+'\n')
 record('controlled_assets_and_local_contact_adaptation_generated',evidence=['research/geometry-generalization-20261002/ASSETS.json','research/geometry-generalization-20261002/GRASPS.json','research/geometry-generalization-20261002/DATA.json'],conditions=len(assets),next='Short static validation; test baseline andT90 input geometry before bulk frozen policy evaluation')
if __name__=='__main__':main()
