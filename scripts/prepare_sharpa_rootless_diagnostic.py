"""Remove only identity fixed empty roots; preserve all shape/joint/grasp data.

The imported empty base has mass1e-7kg and diagonal inertia1e-9kgm2. Removing
that body and its identity fixed constraint is a physics conditioning test,
not an unchanged paper reference. All original assets and failed runs remain.
"""
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'assets/objects/knife_sharpa_official'
    target=root/'assets/objects/knife_sharpa_rootless_20260922'
    cache=root/'caches/initial_grasp/sharpa/knife_sharpa_official'
    new_cache=cache.with_name('knife_sharpa_rootless_20260922')
    assert not target.exists() and not new_cache.exists()
    shutil.copytree(source,target);shutil.copytree(cache,new_cache)
    records=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for i in range(35):
        path=target/('%03d'%i)/'mobility.urdf'
        tree=ET.parse(path);robot=tree.getroot()
        base=robot.find("link[@name='base']");fixed=robot.find("joint[@name='joint_0']")
        assert base is not None and len(base)==0
        assert fixed.get('type')=='fixed' and fixed.find('parent').get('link')=='base' and fixed.find('child').get('link')=='link_0'
        origin=fixed.find('origin')
        assert all(float(v)==0 for field in ['xyz','rpy'] for v in origin.get(field,'0 0 0').split())
        unchanged={e.tag+':'+e.get('name'):ET.tostring(e) for e in robot if e not in [base,fixed]}
        robot.remove(base);robot.remove(fixed)
        assert {e.tag+':'+e.get('name'):ET.tostring(e) for e in robot}==unchanged
        tree.write(path,encoding='utf-8',xml_declaration=True)
        records.append(dict(instance='%03d'%i,original_sha256=sha(source/('%03d'%i)/'mobility.urdf'),rootless_sha256=sha(path)))
    for p in cache.rglob('*'):
        if p.is_file():assert p.read_bytes()==(new_cache/p.relative_to(cache)).read_bytes()
    for label,parent in [('knife_sharpa_rootless_20260922','knife_sharpa_official'),('knife_sharpa_rootless_eval_20260922','knife_sharpa_official_eval')]:
        p=root/'isaacgymenvs/cfg/object'/(label+'.yaml');assert not p.exists()
        p.write_text('defaults:\n  - '+parent+'\n  - _self_\nasset:\n  asset_root: assets/objects/knife_sharpa_rootless_20260922\n')
    record=dict(status='frozen',scope=__doc__,geometries=35,training_geometries=30,heldout_geometries=5,
        instances=records,cache_arrays_and_metadata_unchanged=True,semantic_links_preserved=['link_0','link_1'],
        artifact_sha256={str(p.relative_to(root)):sha(p) for folder in [target,new_cache] for p in folder.rglob('*') if p.is_file()})
    for label in ['knife_sharpa_rootless_20260922','knife_sharpa_rootless_eval_20260922']:
        p=root/'isaacgymenvs/cfg/object'/(label+'.yaml');record['artifact_sha256'][str(p.relative_to(root))]=sha(p)
    out=root/'runs/wuji-goal/sharpa-rootless-dataset-manifest.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(geometries=35,files=len(record['artifact_sha256']))))


if __name__=='__main__':main()
