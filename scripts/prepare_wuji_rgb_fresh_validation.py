"""Freeze both preregistered RGB candidates before generating new unfiltered states."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidates',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output=args.output.resolve()
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    proposal=base/'rgb-fresh-paired-1703-proposal.json';plan=json.loads(proposal.read_text())
    candidates=json.loads(args.candidates.read_text());assert set(candidates)=={'baseline','mixed'}
    assert candidates['baseline']['sha256']==plan['candidates']['baseline']['sha256']
    assert not args.output.exists();args.output.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    frozen={}
    for name,item in candidates.items():
        path=root/item['path'];meta=json.loads(path.with_suffix('.json').read_text())
        audit=json.loads((root/item['fit_audit']).read_text())
        assert audit['status']=='passed' and audit['arms']['rgb']['sha256']==sha(path)==meta['sha256']==item['sha256']
        assert meta['update']==5000 and meta['arm']=='rgb'
        if name=='mixed':assert audit['updates']==5000 and audit['original_initial_weights_matched']
        dest=args.output/'models'/(name+'.pth');dest.parent.mkdir(exist_ok=True)
        shutil.copy2(path,dest);shutil.copy2(path.with_suffix('.json'),dest.with_suffix('.json'))
        assert sha(dest)==item['sha256']
        frozen[name]=dict(item,path=str(dest.relative_to(root)))
    freeze_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (args.output/'frozen-models.json').write_text(json.dumps(dict(created=freeze_time,candidates=frozen),indent=2)+'\n')
    source=root/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy'
    train=np.load(source);assert train.shape==(3,75)
    hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    old_files=[]
    for folder in ['bridge3-evaluation-states','bridge3-fresh200-each-seed20261056','bridge2-evaluation-states',
                   'bridge2-fresh200-each-seeds41-42','functional15-fresh200-seed20261044']:
        old_files+=list((base/folder).glob('*.npy'))
    old_rows=set()
    for path in old_files:
        values=np.load(path);assert values.ndim==2 and values.shape[1]==75
        old_rows.update(map(bytes,values))
    old_rows.update(map(bytes,train))
    pieces=[];splits={};seed=plan['initial_states']['seed'];assert seed==20261120
    for i,name in enumerate(['source','novel16','novel15']):
        stream=int(np.random.SeedSequence([seed,i]).generate_state(1)[0])
        values=states_for_seed(train[i:i+1],stream,hand,trials=100)
        assert values.shape==(100,75) and np.isfinite(values).all() and len(np.unique(values,axis=0))==100
        assert not old_rows.intersection(map(bytes,values));old_rows.update(map(bytes,values))
        path=args.output/(name+'.npy');np.save(path,values);pieces.append(values)
        splits[name]=dict(start=100*i,stop=100*(i+1),trials=100,seed=stream,new_unfiltered_perturbations=True,sha256=sha(path))
    fourth=base/'bridge2-evaluation-states/heldout.npy';held=np.load(fourth);assert held.shape==(32,75)
    pieces.append(held);splits['fourth']=dict(start=300,stop=332,trials=32,reused_development_failure_control=True,sha256=sha(fourth))
    path=args.output/'mixed332.npy';np.save(path,np.concatenate(pieces))
    manifest=dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(),models_frozen=freeze_time,candidates=frozen,
        preregistration_sha256=sha(proposal),source_grasps_sha256=sha(source),seed=seed,splits=splits,
        initial_states_sha256=sha(path),old_cohorts_sha256={str(p.relative_to(root)):sha(p) for p in old_files},
        no_outcome_filter=True,physics_transitions=0,perturbations=dict(position_per_axis_m=.0005,joints_rad=.01,rotation_vector_component_deg=.5),
        protocol=plan['evaluation'],acceptance=plan['acceptance'],generator_sha256=sha(Path(__file__)),
        scope='Three trained grasps and unchanged knife/camera,300 new unfiltered reset perturbations generated after both learned policies froze. Fourth32 are reused failure controls, not independent grasps. No outcome observed at preparation.')
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(args.output)


if __name__=='__main__':main()
