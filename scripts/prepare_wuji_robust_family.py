"""New near-real joint geometry distribution, consistent mass/inertia and grasp IK.
Only static geometry is used to adapt grasps. No policy success is used to filter.
"""
import json, hashlib, shutil, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.prepare_wuji_geometry import adapt
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.wuji_kinematics import WujiKinematics
R=Path(__file__).resolve().parents[1]
D=R/'research/robust-knife-family-20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    base=R/'assets/objects/knife_wuji_real_size_20261002/000'
    meta=json.loads((base/'parameters.json').read_text())
    hand=WujiKinematics();seeds=np.load(R/'research/real-size-student-adaptation-20261002/data/real/adapted-seeds.npy')
    rng=np.random.default_rng(2026100304)
    family=R/'assets/objects/knife_wuji_robust_family_20261003';family.mkdir(exist_ok=False)
    entries=[];lbx={};asset_hashes={}
    # Twelve train geometries plus four held-out geometries, not a full grid.
    dims=np.r_[np.array([[.016,.012,.135],[.014,.010,.130],[.018,.014,.140]]),rng.uniform([.014,.010,.130],[.018,.014,.140],(13,3))]
    for i,size in enumerate(dims):
        sid=f'{i:03d}';f=family/sid;f.mkdir();shutil.copy2(base/'slider-shoulder.obj',f/'slider-shoulder.obj')
        offset=np.zeros(3) if i==0 else np.array([rng.uniform(-.001,.001),0,rng.uniform(-.005,.005)])
        origin=np.array(meta['slider_origin']);origin[1]+=(size[1]-.012)/2;origin+=offset
        height=1. if i<12 else float(rng.uniform(2/3,4/3))
        slider_size=np.array(meta['slider_size']);slider_size[1]*=height
        origin[1]+=(slider_size[1]-.003)/2
        tree=ET.parse(base/'mobility.urdf')
        for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):box.set('size',' '.join(map(str,size)))
        tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)))
        for mesh in tree.findall("./link[@name='link_1']/visual/geometry/mesh")+tree.findall("./link[@name='link_1']/collision/geometry/mesh"):mesh.set('scale',f'1 {height} 1')
        # Constant density around measured-envelope centre; effective mass/inertia are authored.
        mass=.029*float(np.prod(size)/np.prod([.016,.012,.135]));smass=.006*height
        for name,m,dim in [('link_0',mass,size),('link_1',smass,slider_size)]:
            inert=tree.find(f"./link[@name='{name}']/inertial");inert.find('mass').set('value',str(m));v=m/12*np.array([dim[1]**2+dim[2]**2,dim[0]**2+dim[2]**2,dim[0]**2+dim[1]**2])
            for key,value in zip(['ixx','iyy','izz'],v):inert.find('inertia').set(key,str(value))
        tree.write(f/'mobility.urdf',encoding='utf-8',xml_declaration=True)
        adapted=[];diagnostics=[]
        for source,s in enumerate(seeds):
            out,rep=adapt(hand,s,size,origin,np.array([.016,.012,.135]))
            rot=Rotation.from_quat(out[43:47]);out[47:50]=out[40:43]+rot.apply(origin+[0,0,out[54]])
            # Thumb follows contact centre geometry rather than hidden instance metadata.
            oldpoint=hand.contacts(out[:20])[0][0];shift=rot.apply(offset+[0,(slider_size[1]-.003),0])
            q,err=hand.solve_finger('thumb',oldpoint+shift,out[:20]);delta=q-out[:20]
            out[:20]=q;out[20:40]=np.clip(out[20:40]+delta,hand.lower,hand.upper)
            out[55:70]=np.concatenate([t[:3,3] for n,t in hand.forward(q).items() if n in hand.config['track_links']]) if False else np.concatenate([hand.forward(q)[n][:3,3] for n in hand.config['track_links']])
            adapted.append(out);diagnostics.append(dict(source=source,thumb_geometry_ik_error_m=err,**rep))
        adapted=np.array(adapted);cache=R/'caches/initial_grasp/wuji'/family.name/sid;cache.mkdir(parents=True)
        shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_real_size_20261002/000/grasp_state_metadata.json',cache/'grasp_state_metadata.json')
        pools={}
        for split,n,seed in [('train',48,2026100305),('test',12,2026100306)]:
            (cache/split).mkdir();pool=np.concatenate([states_for_seed(adapted[j:j+1],seed*1000+i*10+j,hand,n) for j in range(len(adapted))]);np.save(cache/split/'valid_grasps.npy',pool);pools[split]=dict(path=str((cache/split/'valid_grasps.npy').relative_to(R)),n=len(pool),sha256=sha(cache/split/'valid_grasps.npy'))
        lbx[sid]=size.tolist()+slider_size.tolist()
        (f/'parameters.json').write_text(json.dumps(dict(meta,handle_size=size.tolist(),slider_size=slider_size.tolist(),slider_origin=origin.tolist(),masses=[mass,smass],urdf_sha256=sha(f/'mobility.urdf'),round='robust-knife-family-20261003'),indent=2))
        entries.append(dict(instance=sid,split='train' if i<12 else 'heldout',handle_wtl_m=size.tolist(),slider_center_offset_m=offset.tolist(),slider_height_scale=height,pools=pools,static_ik_diagnostics=diagnostics))
        asset_hashes.update({str(p.relative_to(R)):sha(p) for p in f.iterdir()})
    (family/'lbx.json').write_text(json.dumps(lbx))
    config=R/'isaacgymenvs/cfg/object/knife_wuji_robust_family_20261003.yaml';config.write_text('defaults:\n  - knife_wuji_real_size_20261002\n  - _self_\nasset:\n  asset_root: assets/objects/knife_wuji_robust_family_20261003\n  override_inertia: false\n  instance_id_list: '+json.dumps([e['instance'] for e in entries[:12]])+'\n')
    manifest=dict(seed=2026100304,entries=entries,asset_hashes=asset_hashes,scope='12 sampled near-real train geometries,4 unseen; per-reset continuous physical/contact/noise/load perturbations. All four original functional grasp sources retained; proxy in-hand init, not tabletop handover.',selection='No policy filtering. Static IK errors retained, unavailable grasps counted separately during diagnostics.')
    (D/'family-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(instances=len(entries),sources=len(seeds),manifest_sha256=sha(D/'family-manifest.json'))))
if __name__=='__main__':main()
