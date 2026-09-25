"""Validate provenance and original splits for the approved official Wuji subset."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.filter_wuji_fingertip_grasps import posture_mask,split_membership,RULES

ROOT=Path(__file__).resolve().parents[1]
DATASET='knife_wuji_official_approved'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(instance,require_train=True):
    if len(instance)!=3 or not instance.isdigit() or not 0<=int(instance)<35:
        raise ValueError('Expected an official geometry id 000 through 034')
    if require_train and int(instance)>=30:raise ValueError('Held-out geometry must never enter training')
    cache=ROOT/'caches/initial_grasp/wuji'/DATASET/instance
    source=ROOT/'caches/initial_grasp/wuji/knife_wuji_official'/instance
    report=json.loads((cache/'filter_validation.json').read_text())
    if report['status']!='completed' or report['rules']!=RULES:
        raise ValueError('Instance has no accepted physical validation')
    if sha(source/'valid_grasps.npy')!=report['source_sha256']:
        raise ValueError('Official source data changed')
    if sha(ROOT/'assets/objects/knife_wuji_official'/instance/'mobility.urdf')!=report['urdf_sha256']:
        raise ValueError('Official geometry changed after screening')
    if sha(cache/'screened.npz')!=report['screened_sha256']:
        raise ValueError('Reach-screened states changed')
    for name,digest in report['outputs'].items():
        if sha(cache/name)!=digest:raise ValueError('Filtered output changed: '+name)
    original=np.load(source/'valid_grasps.npy');membership=split_membership(original,source)
    ids=np.load(cache/'source_indices.npy');rows=np.load(cache/'valid_grasps.npy')
    if ids.tolist()!=report['accepted_source_indices'] or not np.array_equal(rows,original[ids]):
        raise ValueError('Accepted rows are not the recorded original rows')
    if rows.shape!=(len(ids),75) or not np.isfinite(rows).all() or not posture_mask(rows).all():
        raise ValueError('Approved posture or state layout failed')
    screened=np.load(cache/'screened.npz');accepted=np.isin(screened['source_indices'],ids)
    if (np.asarray(report['contact_fractions'])[accepted].min()<.9 or
        np.asarray(report['palm_contact_fractions'])[accepted].max()>0 or
        np.asarray(report['max_drift_m'])[accepted].max()>.01 or
        np.asarray(report['max_rotation_rad'])[accepted].max()>.25 or
        np.asarray(report['any_reset'])[accepted].any()):
        raise ValueError('Accepted rows fail the physical stability checks')
    for split in ['train','test']:
        expected=original[ids[membership[ids]==split]]
        actual=np.load(cache/split/'valid_grasps.npy')
        if not np.array_equal(actual,expected):raise ValueError('Original train/test identities changed')
    if require_train and report['train']==0:raise ValueError('No training grasps remain')
    return dict(instance=instance,valid=len(rows),train=report['train'],test=report['test'],
        source_sha256=report['source_sha256'],validation_sha256=sha(cache/'filter_validation.json'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--instances',nargs='+',required=True);a=p.parse_args()
    print(json.dumps([validate(i) for i in a.instances],indent=2))


if __name__=='__main__':main()
