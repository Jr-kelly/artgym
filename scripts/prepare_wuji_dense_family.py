"""Dense independent geometry draws for joint-randomization training.

Geometry is sampled continuously when assets are built, then fixed within each
simulator slot (PhysX collision shapes cannot be resized at episode reset).
512 training shapes replace the small diagnostic cohort; contact/load/noise
remain continuously randomized per episode. No policy-based state filtering.
"""
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
from scripts.prepare_wuji_geometry import adapt
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.record_wuji_robust_goal import record
R=Path(__file__).resolve().parents[1];D=R/'research/robust-knife-family-20261003'
NAME='knife_wuji_dense_acquired_20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=512);p.add_argument('--seed',type=int,default=2026100330);a=p.parse_args()
    assert a.count>=256
    family=R/'assets/objects'/NAME;family.mkdir(exist_ok=False)
    output=D/'dense-family-v1';output.mkdir(exist_ok=False)
    record('dense_geometry_build_started',config=vars(a),evidence=['scripts/prepare_wuji_dense_family.py'],conclusion='Expand from12 diagnostic training shapes to dense draws across joint dimensions/slider offsets; per-slot fixed geometry disclosed, independent four shapes excluded.',next='Generate and hash assets/caches, then train same legal policy with actual50 history')
    base=R/'assets/objects/knife_wuji_real_size_20261002/000';meta=json.loads((base/'parameters.json').read_text())
    hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    sources=np.r_[np.load(R/'research/real-size-student-adaptation-20261002/data/real/adapted-seeds.npy'),np.load(D/'acquired-family-v1/closed-acquired-seed.npy')[None]]
    rng=np.random.default_rng(a.seed);sizes=rng.uniform([.014,.010,.130],[.018,.014,.140],(a.count,3));offsets=np.c_[rng.uniform(-.001,.001,a.count),np.zeros(a.count),rng.uniform(-.005,.005,a.count)]
    sizes[:3]=[[.016,.012,.135],[.014,.010,.130],[.018,.014,.140]];offsets[0]=0
    entries=[];lbx={}
    for i,(size,offset) in enumerate(zip(sizes,offsets)):
        sid=f't{i:04d}';dest=family/sid;dest.mkdir();shutil.copy2(base/'slider-shoulder.obj',dest/'slider-shoulder.obj')
        origin=np.array(meta['slider_origin'])+offset;origin[1]+=(size[1]-.012)/2
        tree=ET.parse(base/'mobility.urdf')
        for node in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):node.set('size',' '.join(map(str,size)))
        tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)))
        mass=.029*np.prod(size)/np.prod([.016,.012,.135]);inert=tree.find("./link[@name='link_0']/inertial");inert.find('mass').set('value',str(mass));diagonal=mass/12*np.array([size[1]**2+size[2]**2,size[0]**2+size[2]**2,size[0]**2+size[1]**2])
        for key,value in zip(['ixx','iyy','izz'],diagonal):inert.find('inertia').set(key,str(value))
        tree.write(dest/'mobility.urdf',encoding='utf-8',xml_declaration=True)
        params=dict(meta,handle_size=size.tolist(),slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),total_size_lwt=[float(size[2]),float(size[0]),float(size[1]+.003)],masses=[float(mass),.006],urdf_sha256=sha(dest/'mobility.urdf'),mass_inertia_mode='Constant handle density relative to nominal .029kg; .006kg slider; authored cuboid diagonal inertia, engineering assumptions',round='robust-knife-family-20261003',generation_seed=a.seed)
        (dest/'parameters.json').write_text(json.dumps(params,indent=2));lbx[sid]=size.tolist()+meta['slider_size']
        adapted=[];diagnostics=[]
        for j,s in enumerate(sources):
            out,diag=adapt(hand,s,size,origin,np.array(meta['handle_size']));rotation=Rotation.from_quat(out[43:47]);out[47:50]=out[40:43]+rotation.apply(origin+[0,0,out[54]])
            point=hand.contacts(out[:20])[0][0];adjusted,err=hand.solve_finger('thumb',point+rotation.apply(offset),out[:20]);delta=adjusted-out[:20]
            out[:20]=adjusted;out[20:40]=np.clip(out[20:40]+delta,hand.lower,hand.upper);out[55:70]=np.concatenate([hand.forward(adjusted)[n][:3,3] for n in hand.config['track_links']]);adapted.append(out);diagnostics.append(dict(source=j,thumb_ik_error_m=err,**diag))
        cache=R/'caches/initial_grasp/wuji'/NAME/sid;cache.mkdir(parents=True)
        shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_acquired_family_20261003/000/grasp_state_metadata.json',cache/'grasp_state_metadata.json')
        pools={}
        for split,seed in [('train',2026100331),('test',2026100332)]:
            path=cache/split/'valid_grasps.npy';path.parent.mkdir()
            pool=np.concatenate([states_for_seed(np.array(s)[None],seed*10000+i*10+j,hand,8 if j==4 else 2) for j,s in enumerate(adapted)]);np.save(path,pool)
            pools[split]=dict(path=str(path.relative_to(R)),sha256=sha(path),n=len(pool))
        entries.append(dict(instance=sid,split='train',dimensions_WTL_m=size.tolist(),slider_center_offset_m=offset.tolist(),asset_hashes={p.name:sha(p) for p in dest.iterdir()},pools=pools,static_adaptation=diagnostics))
        if i%64==0:print(json.dumps(dict(built=i+1,total=a.count)),flush=True)
    heldout_hashes=set()
    for sid in ['012','013','014','015']:
        source=R/'assets/objects/knife_wuji_acquired_family_20261003'/sid;shutil.copytree(source,family/sid);lbx[sid]=json.loads((R/'assets/objects/knife_wuji_acquired_family_20261003/lbx.json').read_text())[sid]
        shutil.copytree(R/'caches/initial_grasp/wuji/knife_wuji_acquired_family_20261003'/sid,R/'caches/initial_grasp/wuji'/NAME/sid)
        heldout_hashes.add(sha(family/sid/'mobility.urdf'))
    assert not heldout_hashes.intersection(e['asset_hashes']['mobility.urdf'] for e in entries)
    (family/'lbx.json').write_text(json.dumps(lbx))
    config=R/'isaacgymenvs/cfg/object'/(NAME+'.yaml');config.write_text('defaults:\n  - knife_wuji_acquired_family_20261003\n  - _self_\nasset:\n  asset_root: assets/objects/'+NAME+'\n  instance_id_list: '+json.dumps([e['instance'] for e in entries])+'\n')
    manifest=dict(name=NAME,args=vars(a),entries=entries,heldout_ids=['012','013','014','015'],heldout_urdf_sha256=sorted(heldout_hashes),heldout_scope='Existing round independent geometry, still not used by policy selection',geometry_distribution='Continuous uniform W14–18,T10–14,L130–140mm; center axial±5/lateral±1mm, sampled at buildtime into512 per-slot shapes; fixed within episode and slot',runtime_distribution='Existing per-reset continuous grasp/contact/load/calibration/noise/delay draws',source_mix='50% actual simulated closed acquisition,50% four original functional sources',selection='No policy filtering; every initialization failure counted',archive_required='Generated assets/caches supplied as Release artifact or rebuilt using this script; not all per-instance files need separate Git blobs')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2));record('dense_geometry_build_finished',evidence=[str((output/'manifest.json').relative_to(R)),str(config.relative_to(R))],manifest_sha256=sha(output/'manifest.json'),config=vars(a),conclusion='Dense joint geometry assets/caches generated; heldout URDF hashes disjoint from all train assets; no policy result used to choose shapes or grasps.',next='Recover useful earlier checkpoint and train dense family with thumb-location reward if early physical failure persists')
if __name__=='__main__':main()
