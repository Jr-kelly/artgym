"""Check saved RGB/label timing against independent pre-reset physics traces."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--reference',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-inactive',action='store_true')
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1]
    status=json.loads((args.run/'collection-status.json').read_text());assert status['status']=='completed'
    fields={};visible=[];nonblack=0;images=0;image_hash=hashlib.sha256()
    for c in status['chunks']:
        f=args.run/c['path'];assert hashlib.sha256(f.read_bytes()).hexdigest()==c['sha256']
        with np.load(f) as z:
            rgb=z['rgb'];assert rgb.dtype==np.uint8 and rgb.shape[0]==c['frames']
            assert rgb.shape[2:]==(320,320,3)
            images+=rgb.shape[0]*rgb.shape[1];nonblack+=int((rgb.max(axis=(2,3,4))>0).sum())
            image_hash.update(rgb.tobytes())
            for k in ['step','known_initial','proprio','goal','target','active','visibility']:
                if k in z:fields.setdefault(k,[]).append(z[k].copy())
    a={k:np.concatenate(v,0) for k,v in fields.items()};steps=a['step']
    assert len(steps)==status['frames'] and images==status['images']==nonblack
    stride=1 if len(steps)==599 else 3;assert np.array_equal(steps,np.arange(1,600,stride))
    valid=a['active'].astype(bool)
    assert valid.any() and np.isfinite(a['target'][valid]).all()
    if not args.allow_inactive:assert valid.all()
    states=np.load(root/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')[status['selected_initial_rows']]
    with np.load(args.run/'trace.npz') as z:
        errors=dict(slider_m=float(np.abs(a['target'][...,6]+states[None,:,54]-z['slider'][steps-1])[valid].max()),
            body_distance_m=float(np.abs(np.linalg.norm(a['target'][...,:3],axis=-1)-z['drift'][steps-1])[valid].max()),
            body_angle_rad=float(np.abs(np.linalg.norm(a['target'][...,3:6],axis=-1)-z['rotation'][steps-1])[valid].max()),
            previous_action=float(np.abs(a['proprio'][...,20:]-z['action'][steps-1])[valid].max()),
            external_goal_m=float(np.abs(a['goal'][...,0]+states[None,:,54]-z['goal'][steps])[valid].max()))
        for key,tolerance in [('slider_m',1e-7),('body_distance_m',1e-7),('body_angle_rad',2e-6),('previous_action',0),('external_goal_m',1e-7)]:
            assert errors[key]<=tolerance,(key,errors[key])
        reference=None
        if args.reference:
            with np.load(args.reference/'trace.npz') as old:
                assert z.files==old.files
                reference={k:bool(np.array_equal(z[k],old[k])) for k in z.files}
                assert all(reference.values()),reference
    result=dict(status='verified',frames=len(steps),images=images,all_rgb_nonblack=True,
        concatenated_rgb_sha256=image_hash.hexdigest(),label_timing_errors=errors,
        teacher_physics_exact_reference=reference,active_images=int(valid.sum()),inactive_images=int((~valid).sum()),
        physics_collection_policy=status.get('physics_collection_policy','frozen_privileged_teacher'),
        slider_visible_images=int((a['visibility'][...,1]>0).sum()) if 'visibility' in a else None,
        slider_pixels_min=int(a['visibility'][...,1].min()) if 'visibility' in a else None,
        slider_pixels_median=float(np.median(a['visibility'][...,1])) if 'visibility' in a else None,
        scope='Active pre-action labels match preceding post-physics samples and next command. Inactive rows stay in evidence and are excluded from fitting. Not real-camera calibration or independent policy success.')
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
