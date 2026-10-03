"""Fresh physical geometry only; no per-asset grasp/actor adaptation."""
import hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.record_wuji_robust_goal import R,D,record


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (D/'freeze.json').exists(),'Prepare preregistered assets before candidate freeze'
    plan=json.loads((D/'independent-validation-plan-v1.json').read_text());config=plan['fresh_geometry_challenge'];count=config['geometry_count'];seed=config['generation_seed'];assert count==128
    source=R/'assets/objects/knife_wuji_real_size_20261002/000';meta=json.loads((source/'parameters.json').read_text());family=R/'assets/objects/knife_wuji_dense_under_20261003'
    assert not any((family/f'h{i:04d}').exists() for i in range(count))
    record('fresh_independent_geometry_preparation_started',config=config,conclusion='Freshphysicaldraws only; sameactorandnominalgrasp/calibrationplanned. No static per-asset IK, teacher labeling or policy filtering.',next='Hashassetswithoutopeninganyrollout; freezecandidatebeforeexecution')
    rng=np.random.default_rng(seed);sizes=rng.uniform([.014,.010,.130],[.018,.014,.140],(count,3));offsets=np.c_[rng.uniform(-.001,.001,count),np.zeros(count),rng.uniform(-.005,.005,count)];entries=[]
    train_hashes={sha(family/f't{i:04d}'/'mobility.urdf') for i in range(512)}
    for i,(size,offset) in enumerate(zip(sizes,offsets)):
        sid=f'h{i:04d}';dest=family/sid;dest.mkdir();shutil.copy2(source/'slider-shoulder.obj',dest/'slider-shoulder.obj')
        origin=np.array(meta['slider_origin'])+offset;origin[1]+=(size[1]-.012)/2;tree=ET.parse(source/'mobility.urdf')
        for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):box.set('size',' '.join(map(str,size)))
        tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)))
        mass=.029*float(np.prod(size)/np.prod([.016,.012,.135]));inert=tree.find("./link[@name='link_0']/inertial");inert.find('mass').set('value',str(mass));diag=mass/12*np.array([size[1]**2+size[2]**2,size[0]**2+size[2]**2,size[0]**2+size[1]**2])
        for key,value in zip(['ixx','iyy','izz'],diag):inert.find('inertia').set(key,str(value))
        tree.write(dest/'mobility.urdf',encoding='utf-8',xml_declaration=True);asset_hash=sha(dest/'mobility.urdf');assert asset_hash not in train_hashes
        params=dict(meta,id=sid,split='heldout-fresh',handle_size=size.tolist(),slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),total_size_lwt=[float(size[2]),float(size[0]),float(size[1]+.003)],masses=[mass,.006],urdf_sha256=asset_hash,generation_seed=seed,mass_inertia_mode='Same authored constant-density cuboid approximation as training; not measured real mass/inertia',scope='Physical validation asset only; no actor asset-ID or geometry update, no asset-specific initial grasp')
        (dest/'parameters.json').write_text(json.dumps(params,indent=2));entries.append(dict(instance=sid,path=str(dest.relative_to(R)),hashes={f.name:sha(f) for f in dest.iterdir()}))
    manifest=dict(count=count,seed=seed,entries=entries,training_urdf_hashes_disjoint=True,scope='All predeclared128 draws kept. Nearby continuous dimensions/slider positions; not cross-model/category or guaranteed distant-from-training shapes. No rollout inspected before candidate freeze.')
    out=D/'fresh-validation-assets-v1.json';out.write_text(json.dumps(manifest,indent=2));record('fresh_independent_geometry_preparation_completed',evidence=str(out.relative_to(R)),manifest_sha256=sha(out),config={'count':count,'seed':seed},conclusion='128newphysicalassets hashed, exactURDFhashesdisjointfrom512trainingassets; everydrawretained',next='Onecandidatefreeze beforeopeningfreshor012-015rollouts')


if __name__=='__main__':main()
