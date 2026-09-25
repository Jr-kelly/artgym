"""Expose unchanged official geometry under the separately screened cache name."""
import json,os
from pathlib import Path
from scripts.check_official_wuji_transfer import ROOT,DATASET,validate,sha
from scripts.monitor_wuji_checkpoints import atomic_json,now


def main():
    state=json.loads((ROOT/'runs/wuji-goal/official-screen/status.json').read_text())
    if state['status']!='completed' or len(state['physical_completed'])!=35 or state['failed']:
        raise ValueError('Wait for all 35 physical-screen jobs to finish')
    output=ROOT/'assets/objects'/DATASET;output.mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/objects/knife_wuji_official'
    records=[];empty=[]
    for i in range(35):
        instance=f'{i:03d}'
        report=json.loads((ROOT/'caches/initial_grasp/wuji'/DATASET/instance/'filter_validation.json').read_text())
        if report['valid']:
            records.append(validate(instance,require_train=i<30))
        else:empty.append(instance)
    names=[f'{i:03d}' for i in range(35)]+['lbx.json']
    if (source/'bbx.json').exists():names.append('bbx.json')
    for name in names:
        target=source/name;link=output/name
        if not target.exists():raise FileNotFoundError(target)
        if link.exists() or link.is_symlink():
            if link.resolve()!=target.resolve():raise ValueError('Existing asset points elsewhere: '+str(link))
        else:link.symlink_to(os.path.relpath(target,output),target_is_directory=target.is_dir())
    manifest=dict(created=now(),dataset=DATASET,geometry_source='knife_wuji_official',
        geometry_modified=False,original_training_ids=[f'{i:03d}' for i in range(30)],
        original_heldout_ids=[f'{i:03d}' for i in range(30,35)],
        available_training_ids=[r['instance'] for r in records if int(r['instance'])<30 and r['train']>0],
        available_heldout_geometry_ids=[r['instance'] for r in records if int(r['instance'])>=30],
        empty_after_user_filter=empty,records=records,
        note='Separate Wuji migration screening; empty geometries are reported, never counted as learned successes')
    atomic_json(output/'manifest.json',manifest);print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
