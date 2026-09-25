"""Audit initial-to-path continuity without changing any train/validation rows.

The old reach screen solves each waypoint independently enough to jump between
thumb postures. This reports that limitation and tries a fixed material contact
point, seeded at the actual initial thumb joints, with bounded incremental IK.
This remains a kinematic diagnostic, not a contact-dynamics success test.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.filter_wuji_fingertip_grasps import ThumbReach
from scripts.monitor_wuji_checkpoints import atomic_json

ROOT=Path(__file__).resolve().parents[1]


def anchored_path(reach,state,metadata,travel=.04):
    q0=state[16:20].astype(float);r=Rotation.from_quat(state[43:47]).as_matrix()
    f0=reach.frame(q0);vertices=reach.vertices@f0[:3,:3].T+f0[:3,3]
    slider_origin=np.asarray(metadata['slider_origin'])+np.array([0,0,state[54]])
    local=(vertices-state[40:43])@r-slider_origin
    size=np.asarray(metadata['slider_size'])
    # Choose actual mesh vertices closest to the current slider top rectangle.
    projected=local.copy();projected[:,0]=np.clip(projected[:,0],-size[0]/2,size[0]/2)
    projected[:,1]=size[1]/2;projected[:,2]=np.clip(projected[:,2],-size[2]/2,size[2]/2)
    distance=np.linalg.norm(projected-local,axis=1)
    near=distance<=distance.min()+.00025
    point_local=reach.vertices[near].mean(0)
    world_start=f0[:3,:3]@point_local+f0[:3,3]
    q=q0.copy();path=[q.tolist()];errors=[0.];travel_points=np.linspace(0,travel,41)
    max_step=.075 # at least three 30 Hz control steps at the trained thumb limit
    for displacement in np.r_[travel_points[1:],travel_points[-2::-1]]:
        target=world_start+r[:,2]*displacement;previous=q.copy()
        def residual(values):
            frame=reach.frame(values);point=frame[:3,:3]@point_local+frame[:3,3]
            return np.r_[(point-target)/.001,.025*(values-previous)/max_step]
        lo=np.maximum(reach.hand.lower[16:],previous-max_step)
        hi=np.minimum(reach.hand.upper[16:],previous+max_step)
        result=least_squares(residual,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=80)
        q=result.x;frame=reach.frame(q);error=np.linalg.norm(frame[:3,:3]@point_local+frame[:3,3]-target)
        path.append(q.tolist());errors.append(float(error))
        if error>.002:break
    return dict(passed=len(path)==81 and max(errors)<=.002,points=len(path),
        initial_surface_gap_m=float(distance.min()),max_error_m=max(errors),max_joint_step_rad=max_step,
        material_contact_point=point_local.tolist(),thumb_path_rad=path,errors_m=errors)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cache=ROOT/'caches/initial_grasp/wuji/knife_wuji_fingertip/000'
    full=np.load(cache/'valid_grasps.npy');ids=np.load(cache/'source_indices.npy')
    old=json.loads((cache/'screening.json').read_text())['reach_results']
    old={r['source_index']:r for r in old};reach=ThumbReach()
    meta=json.loads((ROOT/'assets/objects/knife_wuji_fingertip/000/parameters.json').read_text())
    records=[]
    for split in ['train','test']:
        for index,row in enumerate(np.load(cache/split/'valid_grasps.npy')):
            source=int(ids[np.flatnonzero((full==row).all(1))[0]]);legacy=old[source]
            path=np.asarray(legacy['thumb_path_rad'])
            record=dict(split=split,grasp_index=index,source_index=source,
                old_initial_max_joint_jump_rad=float(abs(path[0]-row[16:20]).max()),
                old_path_max_joint_jump_rad=float(abs(np.diff(path,axis=0)).max()),
                continuous=anchored_path(reach,row,meta))
            records.append(record)
    report=dict(protocol=__doc__,records=records,source_dataset='knife_wuji_fingertip/000',
        original_data_modified=False)
    atomic_json(args.output,report)
    print(json.dumps([dict(split=r['split'],index=r['grasp_index'],initial_jump=r['old_initial_max_joint_jump_rad'],
        path_jump=r['old_path_max_joint_jump_rad'],continuous_pass=r['continuous']['passed'],points=r['continuous']['points']) for r in records]))


if __name__=='__main__':main()
