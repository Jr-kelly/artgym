"""Fresh registered cohorts and controlled assets; never reads historical finals."""
import copy
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from scripts.prepare_wuji_geometry import adapt, meshes, penetration
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_width_contract import ROUND, sha, slots
from scripts.record_wuji_width_goal import R, D, record


def main():
    plan = dict(round=ROUND, train=dict(seed=2026100211, attempts_per_source=512, take=256),
                dev=dict(seed=2026100212, attempts_per_source=64, take=32),
                confirm=dict(seed=2026100213, attempts_per_source=128, take=64),
                final=dict(seed=2026100214, attempts_per_source_seen=192, take_seen=128,
                           attempts_per_source_unseen=128, take_unseen=64),
                optimization_seeds=[2026100215, 2026100216],
                geometries=dict(baseline=[147,19,8], W110=[147,20.9,8], W120=[147,22.8,8],
                                W115=[147,21.85,8], W115_T110=[147,21.85,8.8]),
                sources=[0,1,2,3], protocols=['F','S2','S5'], paired_slots=dict(C=slots('C'),G=slots('G')),
                video_dev_rows=dict(baseline_source3='first accepted', W120_source3='first accepted'),
                final_access='Only static structural checks before freeze; policy access once after candidate/matched-control/plan freeze',
                static_rule='first valid order; no policy selection;2s drift<.01m/rotation<.25rad, finite/joint ±2e-6, baseline penetration proxy+1mm, thumb local IK<=2mm',
                first_window=dict(start=51200,endpoint=54400,saves=[52000,52800,54400],added_updates=3200,added_transitions_per_arm=3276800),
                formal_registration='Endpoint may only be uniformly shortened before formal training if measured complete throughput cannot fit both arms/dev and6GPUh reserve')
    assert not (D/'DATA_PLAN.json').exists(), 'Resume existing data; do not regenerate'
    (D/'DATA_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    record('fresh_cohorts_preregistered_and_preparation_started', evidence='research/'+ROUND+'/DATA_PLAN.json',
           next='Generate fixed recipes and fresh perturbations; static validity is not yet verified')
    original = R/'assets/objects/knife_wuji_bridge3_20260922'
    base_meta = json.loads((original/'000/parameters.json').read_text())
    base = np.asarray(base_meta['handle_size']); origin0=np.asarray(base_meta['slider_origin'])
    seeds = np.load(R/'research/multigrasp-20260928/data/candidates.npy')[:4]
    hand = WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    mesh=meshes(hand); assets={}; grasps={}; entries=[]; seen=set()
    for label, lwt in plan['geometries'].items():
        size=np.asarray([lwt[1],lwt[2],lwt[0]])/1000
        origin=origin0.copy();origin[1]+=(size[1]-base[1])/2
        name='knife_wuji_width_'+label+'_20261002';folder=R/'assets/objects'/name
        (folder/'000').mkdir(parents=True,exist_ok=False)
        tree=ET.parse(original/'000/mobility.urdf')
        for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):
            box.set('size',' '.join(map(str,size)))
        tree.find("./joint[@name='slider']/origin").set('xyz',' '.join(map(str,origin)))
        urdf=folder/'000/mobility.urdf'
        if label=='baseline':shutil.copy2(original/'000/mobility.urdf',urdf)
        else:tree.write(urdf,encoding='utf-8',xml_declaration=True)
        meta=copy.deepcopy(base_meta);meta.update(round=ROUND,label=label,handle_size=size.tolist(),slider_origin=origin.tolist(),
            slider_initial_center=(origin+[0,0,base_meta['joint_lower']]).tolist(),total_size_lwt=[size[2],size[0],size[1]+.003],
            urdf_sha256=sha(urdf),mass_inertia_mode='measured baseline effective inertia frozen after load',
            axes='URDF W/T/L; policy W/L/T',thickness_coupling='jointY half-thickness difference; longitudinal origin fixed')
        (folder/'000/parameters.json').write_text(json.dumps(meta,indent=2)+'\n')
        (folder/'lbx.json').write_text(json.dumps({'000':size.tolist()+meta['slider_size']})+'\n')
        config=R/'isaacgymenvs/cfg/object'/(name+'.yaml')
        config.write_text('defaults:\n  - knife_wuji_bridge3_20260922\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000']\n")
        adapted=[]; reports=[]
        for source,s in enumerate(seeds):
            out,rep=(s.copy(),dict(contact_errors_m=[0]*5)) if label=='baseline' else adapt(hand,s,size,origin,base)
            rep.update(source=source,thumb_reach_valid=rep['contact_errors_m'][0]<=.002,
                       baseline_vertex_penetration_m=penetration(hand,mesh,s,base,origin0),
                       new_vertex_penetration_m=penetration(hand,mesh,out,size,origin))
            adapted.append(out);reports.append(rep)
        directory=D/'data'/label;directory.mkdir(parents=True,exist_ok=False)
        np.save(directory/'adapted-seeds.npy',adapted)
        cache=R/'caches/initial_grasp/wuji'/name/'000';cache.mkdir(parents=True)
        shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/grasp_state_metadata.json',cache/'grasp_state_metadata.json')
        for split in ['train','test']:
            (cache/split).mkdir();np.save(cache/split/'valid_grasps.npy',adapted)
        split_names=['train','dev','confirm','final'] if label in ['baseline','W110','W120'] else ['final']
        for split in split_names:
            spec=plan[split]; seed=spec['seed'];count=spec.get('attempts_per_source',spec.get('attempts_per_source_seen' if label in ['baseline','W110','W120'] else 'attempts_per_source_unseen'))
            chunks=[];hashes=[]
            for source,s in enumerate(adapted):
                rows=states_for_seed(np.asarray(s)[None],seed*100+source,hand,trials=count);chunks.append(rows)
                for row in rows:
                    digest=__import__('hashlib').sha256(row.tobytes()).hexdigest()
                    assert (label,digest) not in seen;seen.add((label,digest));hashes.append(digest)
            path=directory/(split+'-attempts.npy');np.save(path,np.concatenate(chunks))
            entries.append(dict(label=label,split=split,attempts_per_source=count,seed=seed,path=str(path.relative_to(R)),sha256=sha(path),
                                source_order=[s for s in range(4) for _ in range(count)],row_sha256=hashes,
                                static_validated=False,policy_access=False,training_allowed=split=='train'))
        assets[label]=dict(object=name,dimensions_mm_LWT=lwt,parameters=meta,files={str(p.relative_to(R)):sha(p) for p in [*folder.rglob('*'),config] if p.is_file()})
        grasps[label]=reports
    # Three instances keep the existing ArtManip asset/cache/bbox paths intact.
    packed=R/'assets/objects/knife_wuji_width_train_20261002';packed.mkdir()
    lbx={};files={}
    for index,label in enumerate(['baseline','W110','W120']):
        instance='%03d'%index;entry=assets[label]
        shutil.copytree(R/'assets/objects'/entry['object']/'000',packed/instance)
        lbx[instance]=entry['parameters']['handle_size']+entry['parameters']['slider_size']
        shutil.copytree(R/'caches/initial_grasp/wuji'/entry['object']/'000',R/'caches/initial_grasp/wuji/knife_wuji_width_train_20261002'/instance)
    (packed/'lbx.json').write_text(json.dumps(lbx)+'\n')
    for p in packed.rglob('*'):
        if p.is_file():files[str(p.relative_to(R))]=sha(p)
    (D/'ASSETS.json').write_text(json.dumps(assets,indent=2)+'\n')
    (D/'GRASPS.json').write_text(json.dumps(grasps,indent=2)+'\n')
    (D/'DATA.json').write_text(json.dumps(dict(round=ROUND,entries=entries,unique_rows=len(seen),historical_final_access=False,
        pairing='same seed*100+source perturbation lineage across geometry; geometry-adapted physical states differ',
        recipe='joint ±.01rad, translation ±.5mm/axis, rotvec ±.5deg/axis; original small perturbation clusters',
        packed_asset_files=files),indent=2)+'\n')
    record('fresh_cohorts_and_controlled_assets_generated',evidence=['research/'+ROUND+'/ASSETS.json','research/'+ROUND+'/GRASPS.json','research/'+ROUND+'/DATA.json'],
           state_updates=dict(fresh_data_generated=True,static_validation_complete=False),
           next='Run2s static acceptance; assemble training manifests only from accepted rows; H200 paired precheck still pending connectivity')


if __name__=='__main__':main()
