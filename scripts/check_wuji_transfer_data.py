"""Gate multi-grasp transfer on the user's approved direction and cached validation."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def validate(instance):
    from scripts.filter_wuji_fingertip_grasps import posture_mask,RULES
    cache=ROOT/'caches/initial_grasp/wuji/knife_wuji_fingertip'/instance
    validation=json.loads((cache/'filter_validation.json').read_text())
    if validation['rules']!=RULES:raise ValueError('Unrecognized posture validation')
    for name,digest in validation['outputs'].items():
        if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Validated output changed: '+name)
    source=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_paper'/instance/'valid_grasps.npy')
    ids=np.load(cache/'source_indices.npy');retained=np.load(cache/'valid_grasps.npy')
    if ids.tolist()!=validation['accepted_source_indices'] or not np.array_equal(retained,source[ids]):
        raise ValueError('Original validated source identity changed')
    screened=np.load(cache/'screened.npz');selected=np.isin(screened['source_indices'],ids)
    if (np.asarray(validation['contact_fractions'])[selected].min()<.9 or
            np.asarray(validation['palm_contact_fractions'])[selected].max()>0 or
            np.asarray(validation['max_drift_m'])[selected].max()>.01 or
            np.asarray(validation['max_rotation_rad'])[selected].max()>.25):
        raise ValueError('Accepted rows fail the recorded physical thresholds')
    records={}
    for split in ['train','test']:
        relative=split+'/valid_grasps.npy';path=cache/relative
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=validation['outputs'][relative]:raise ValueError('Validated states changed')
        states=np.load(path)
        direction=Rotation.from_quat(states[:,43:47]).apply([0,0,1])[:,1]
        if states.shape[1]!=75 or not np.isfinite(states).all() or not (direction>=.82).all():
            raise ValueError('Invalid or opposite-direction grasp')
        if not (states[:,42]>=.095).all():raise ValueError('Not the approved fingertip posture')
        if not posture_mask(states).all():raise ValueError('Outside the approved pose envelope')
        records[split]=dict(count=len(states),minimum_thumbwards_dot=float(direction.min()),sha256=digest)
    record=dict(status='passed',checked=now(),dataset='knife_wuji_fingertip',instance=instance,
        provenance='Previously generated and validated Wuji fingertip subset; not the new official func_lygra dataset',
        validation_source=str((cache/'filter_validation.json').relative_to(ROOT)),
        validation_sha256=hashlib.sha256((cache/'filter_validation.json').read_bytes()).hexdigest(),splits=records)
    return record


def main():
    p=argparse.ArgumentParser();p.add_argument('--instance',default='000');a=p.parse_args()
    record=validate(a.instance)
    atomic_json(ROOT/'runs/wuji-goal/data-gates'/('fingertip-'+a.instance+'.json'),record)
    print(json.dumps(record))


if __name__=='__main__':main()
