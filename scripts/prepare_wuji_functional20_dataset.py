"""Freeze physically screened training grasps without mixing source splits.

17 old training-source settled states plus three fresh training-source states;
one fresh held-out state. The original five failed validation sources remain a
separate unchanged benchmark. This dataset is static-feasibility evidence, not
successful multi-grasp manipulation, and one feasible test grasp is inadequate
to establish broad generalization. Further fresh seeds are collected separately.
"""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]
    base=root/'runs/wuji-goal/diagnostics'
    old=base/'lowgain-settled-grasps-v1'
    fresh=base/'fresh-lowgain-functional-generation/independent-quality-v2'
    groups=[('settled_train_sources',old/'joined-quality-report.json',old/'candidates/initial_states.npy'),
            ('fresh_seed20261018',fresh/'report.json',fresh/'candidates/initial_states.npy')]
    selected={'train':[],'test':[]};records=[];sources={}
    for name,report_path,array_path in groups:
        report=json.loads(report_path.read_text());assert report['status']=='completed'
        states=np.load(array_path)
        assert hashlib.sha256(array_path.read_bytes()).hexdigest()==report['initial_states_sha256']
        for row in report['records']:
            if not row['all_gates_pass']:continue
            i=row['candidate_row'];split=row['split']
            assert split in ['train','test']
            selected[split].append(states[i])
            records.append(dict(group=name,split=split,candidate_row=i,source=str(array_path.relative_to(root)),
                                dataset_split_row=len(selected[split])-1))
        for p in [report_path,array_path]:sources[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    train=np.stack(selected['train']);test=np.stack(selected['test'])
    assert train.shape==(20,75) and test.shape==(1,75)
    assert np.isfinite(train).all() and np.isfinite(test).all()
    assert not ({r.tobytes() for r in train}&{r.tobytes() for r in test})
    name='knife_wuji_lowgain_functional20_20260922'
    asset=root/'assets/objects'/name
    cache=root/'caches/initial_grasp/wuji'/name/'000'
    assert not asset.exists() and not cache.exists(), 'Frozen datasets cannot be replaced'
    original=root/'assets/objects/knife_wuji_fingertip'
    fresh_asset=root/'assets/objects/knife_wuji_lowgain_fresh20260922'
    assert (original/'000/mobility.urdf').read_bytes()==(fresh_asset/'000/mobility.urdf').read_bytes()
    shutil.copytree(original/'000',asset/'000')
    (asset/'lbx.json').write_text(json.dumps({'000':json.loads((original/'lbx.json').read_text())['000']},indent=2)+'\n')
    for split,data in [('train',train),('test',test),('valid',np.concatenate([train,test]))]:
        p=cache/split;p.mkdir(parents=True,exist_ok=True);np.save(p/'valid_grasps.npy',data)
    np.save(cache/'valid_grasps.npy',np.concatenate([train,test]))
    (cache/'grasp_state_metadata.json').write_text(json.dumps(dict(pose_frame='hand_base'))+'\n')
    result=dict(status='frozen',scope=__doc__,dataset=name,train_count=20,test_count=1,records=records,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256=sources,
        geometry_sha256=hashlib.sha256((asset/'000/mobility.urdf').read_bytes()).hexdigest(),
        artifact_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in cache.rglob('*') if p.is_file()},
        next_gate='Actual training-env reset/control checks and a bounded PPO preflight before any training launch')
    (cache/'dataset-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/'runs/wuji-goal/functional20-dataset-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(dataset=name,train=20,test=1,geometry_sha256=result['geometry_sha256'])))


if __name__=='__main__':main()
