"""Filter immutable paper grasps against the approved fingertip preview.

This is a user-specific subset of the published protocol. Kinematic slider
reach is an initial-state screen, not evidence that a learned policy succeeds.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from scripts.wuji_kinematics import ROOT, WujiKinematics

SOURCE = ROOT/'caches/initial_grasp/wuji/knife_wuji_paper'
TARGET_NAME = 'knife_wuji_fingertip'
TARGET = ROOT/'caches/initial_grasp/wuji'/TARGET_NAME
ASSETS = ROOT/'assets/objects'/TARGET_NAME
RULES = dict(version='approved_fingertip_v1', blade_thumb_side_min_dot=.82,
             max_reference_rotation_deg=40., max_reference_center_distance_m=.035,
             min_center_height_m=.095, thumb_travel_m=.04, thumb_reach_tolerance_m=.002,
             slider_edge_margin_m=.001,
             validation_seconds=2., max_drift_m=.01, max_rotation_rad=.25,
             min_each_fingertip_contact_fraction=.9, max_palm_contact_fraction=0.,
             contact_sample_control_steps=3, contact_force_threshold=1e-6)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2)); temp.replace(path)


def implementation_digest(*items):
    return hashlib.sha256(''.join(inspect.getsource(item) for item in items).encode()).hexdigest()


def input_signature(instance):
    source=SOURCE/instance
    paths=[source/p for p in ('valid_grasps.npy','train/valid_grasps.npy','test/valid_grasps.npy','grasp_state_metadata.json')]
    paths+=sorted(p for p in (ASSETS/instance).rglob('*') if p.is_file())
    paths+=sorted(p for p in (ROOT/'assets/hands/wuji_artbot').rglob('*') if p.is_file())
    paths+=[ROOT/'isaacgymenvs/cfg'/p for p in ('hand/wuji.yaml','hand/wuji_paper.yaml','object/knife.yaml',
                                            'object/knife_wuji_paper.yaml','task/artmanip.yaml','task/artgrasp.yaml')]
    paths+=[SOURCE/'000/valid_grasps.npy']
    return dict(files={str(p.relative_to(ROOT)):digest(p) for p in paths},rules=RULES,
                screening_implementation=implementation_digest(posture_mask,ThumbReach,split_membership))


def reference():
    return np.load(SOURCE/'000/valid_grasps.npy')[52].astype(np.float64)


def posture_mask(rows):
    ref = reference()
    rotations = Rotation.from_quat(rows[:,43:47])
    delta = (rotations*Rotation.from_quat(ref[43:47]).inv()).magnitude()
    return ((rotations.as_matrix()[:,1,2]>=RULES['blade_thumb_side_min_dot'])
            & (delta<=np.deg2rad(RULES['max_reference_rotation_deg']))
            & (np.linalg.norm(rows[:,40:43]-ref[40:43],axis=1)<=RULES['max_reference_center_distance_m'])
            & (rows[:,42]>=RULES['min_center_height_m']))


def split_membership(rows, folder):
    train = {row.tobytes() for row in np.load(folder/'train/valid_grasps.npy')}
    test = {row.tobytes() for row in np.load(folder/'test/valid_grasps.npy')}
    if train & test: raise ValueError('Original train/test grasp pools overlap')
    result = []
    for row in rows:
        key = row.tobytes()
        if key not in train|test: raise ValueError('Source grasp has no original split')
        result.append('train' if key in train else 'test')
    return np.asarray(result)


class ThumbReach:
    def __init__(self):
        self.hand = WujiKinematics()
        self.chain = [j for j in self.hand.joints if '_thumb_' in j[1]]
        name = 'hand_r_thumb_pad_link'
        path = ROOT/'assets/hands/wuji_artbot/meshes/collision'/f'{name}.obj'
        self.vertices = np.array([np.fromstring(s[2:],sep=' ') for s in path.read_text().splitlines() if s.startswith('v ')])

    def frame(self, q):
        frame = np.eye(4)
        for _, _, origin, index, axis in self.chain:
            t = origin.copy()
            if index is not None: t[:3,:3] = t[:3,:3]@Rotation.from_rotvec(axis*q[index-16]).as_matrix()
            frame = frame@t
        return frame

    def check(self, state, meta):
        hand = self.hand
        rotation = Rotation.from_quat(state[43:47]).as_matrix()
        normal = rotation[:,1]
        center = state[40:43]
        slider_start = np.asarray(meta['slider_origin'])+np.array([0.,0.,state[54]])
        # Try three longitudinal positions within the real slider top face.
        # Keep each chosen contact point fixed relative to the slider along the path.
        z_extent = meta['slider_size'][2]/2-RULES['slider_edge_margin_m']
        offsets = [0., -.5*z_extent, .5*z_extent]
        best = dict(passed=False,max_error_m=float('inf'))
        for offset in offsets:
            q = state[16:20].astype(np.float64).copy(); qs=[]; errors=[]; normals=[]
            travel_points=np.linspace(0,RULES['thumb_travel_m'],9)
            for travel in np.r_[travel_points,travel_points[-2::-1]]:
                target = center+rotation@(slider_start+[0.,meta['slider_size'][1]/2,offset+travel])
                def residual(v):
                    frame = self.frame(v)
                    vertices = self.vertices@frame[:3,:3].T+frame[:3,3]
                    point = vertices.mean(0)
                    point += normal*((vertices@normal).min()-point@normal)
                    return np.r_[(point-target)*100,(frame[:3,0]+normal)*.08]
                fit = least_squares(residual,np.clip(q,hand.lower[-4:]+1e-7,hand.upper[-4:]-1e-7),
                                    bounds=(hand.lower[-4:],hand.upper[-4:]),max_nfev=60)
                q=fit.x; errors.append(float(np.linalg.norm(fit.fun[:3])/100))
                normals.append(float(self.frame(q)[:3,0]@(-normal))); qs.append(q.tolist())
                if errors[-1]>RULES['thumb_reach_tolerance_m']: break
            # Contact uses the actual pad support surface, which may be a side
            # face. Its link +X axis is not itself the contact normal.
            report = dict(passed=len(errors)==17 and max(errors)<=RULES['thumb_reach_tolerance_m'],
                          max_error_m=max(errors),min_normal_dot=min(normals),slider_contact_offset_z_m=offset,
                          thumb_path_rad=qs)
            if report['passed']: return report
            if report['max_error_m']<best['max_error_m']:best=report
        return best


def prepare():
    ASSETS.mkdir(parents=True,exist_ok=True);TARGET.mkdir(parents=True,exist_ok=True)
    source_assets=ROOT/'assets/objects/knife_wuji_paper'
    for p in source_assets.iterdir():
        if p.is_dir():shutil.copytree(p,ASSETS/p.name,dirs_exist_ok=True)
        else:shutil.copy2(p,ASSETS/p.name)
    manifest=json.loads((ASSETS/'manifest.json').read_text())
    manifest['grasp_filter']=dict(rules=RULES,reference_instance='000',reference_valid_index=52,
                                original_asset_dir='knife_wuji_paper')
    save_json(ASSETS/'manifest.json',manifest)


def screen(instance):
    start=time.time();source=SOURCE/instance;output=TARGET/instance;output.mkdir(parents=True,exist_ok=True)
    rows=np.load(source/'valid_grasps.npy');splits=split_membership(rows,source);meta=json.loads((ASSETS/instance/'parameters.json').read_text())
    signature=input_signature(instance)
    if (output/'screening.json').exists():
        previous=json.loads((output/'screening.json').read_text())
        if (previous['signature']==signature and (output/'screened.npz').exists()
                and previous.get('screened_sha256')==digest(output/'screened.npz')):
            print(instance,'already screened',previous['reachable'],flush=True);return
    ids=np.flatnonzero(posture_mask(rows));reach=ThumbReach();selected=[];reports=[]
    for index in ids:
        result=reach.check(rows[index].astype(np.float64),meta)
        reports.append(dict(source_index=int(index),**result))
        if result['passed']:selected.append(index)
    selected=np.asarray(selected,dtype=int)
    np.savez(output/'screened.npz',states=rows[selected],source_indices=selected,splits=splits[selected])
    save_json(output/'screening.json',dict(signature=signature,screened_sha256=digest(output/'screened.npz'),original=len(rows),posture_eligible=len(ids),reachable=len(selected),
                                         retained_train=int((splits[selected]=='train').sum()),retained_test=int((splits[selected]=='test').sum()),
                                         seconds=time.time()-start,reach_results=reports))
    print(instance,'posture',len(ids),'reachable',len(selected),'train',int((splits[selected]=='train').sum()),'seconds',round(time.time()-start,1),flush=True)


def physical(instance, images=False):
    # Isaac Gym must be imported before torch, in a fresh process for each object.
    import isaacgym
    from isaacgym import gymapi
    import torch
    from hydra import compose, initialize_config_dir
    from isaacgymenvs.tasks.artgrasp import ArtGrasp
    import isaacgymenvs
    from omegaconf import OmegaConf
    from PIL import Image
    output=TARGET/instance;data=np.load(output/'screened.npz');rows=data['states'];count=len(rows)
    if not count:raise ValueError(f'{instance}: no kinematically eligible grasps')
    if json.loads((output/'screening.json').read_text())['signature']!=input_signature(instance):
        raise ValueError(f'{instance}: screening is stale; rerun screen')

    class FilterValidation(ArtGrasp):
        def _prepare_output_dirs(self): pass
        def _load_init_states(self):
            self.validation_total_candidates=count
            self.validation_total_batches=1
            self.saved_grasping_states=[torch.as_tensor(rows,device=self.device)]
            self.grasp_len_per_instance=[count]
            self.instance_grasp_state_pose_is_local=torch.ones(1,dtype=torch.bool,device=self.device)

    isaacgymenvs.register_omegaconf_resolvers()
    with initialize_config_dir(version_base='1.1',config_dir=str(ROOT/'isaacgymenvs/cfg')):
        cfg=compose('config',overrides=['task=artgrasp','train=wujiKnifeSAPG','hand=wuji_paper','object=knife_wuji_paper',
             f'asset_dir={TARGET_NAME}',f"object.asset.instance_id_list=['{instance}']",f'task.env.numEnvs={count}',
             'task.env.episodeLength=61','pipeline=cpu','headless=True','task.env.forceScale=0','task.env.jointNoise=0',
             'task.task.randomize=False','hand.randomization.randomize=False','object.randomization.randomize=False',
             f'task.env.enableCameraSensors={images}'])
    full_cfg=OmegaConf.to_container(cfg,resolve=True)
    task_cfg=full_cfg['task']
    for key in ('hand','object','train','experiment'):
        task_cfg[key]=full_cfg[key]
    task_cfg['object']['asset']['asset_root']=str(ASSETS.relative_to(ROOT))
    task_cfg['env']['camera'].update(height=384,width=384,horizontal_fov=45)
    from isaacgymenvs.utils.utils import set_seed
    set_seed(20260920)
    steps=round(RULES['validation_seconds']/(task_cfg['sim']['dt']*task_cfg['env']['controlFrequencyInv']))
    task_cfg['env']['episodeLength']=steps+1
    env=FilterValidation(cfg=task_cfg,rl_device='cuda:0',sim_device='cuda:0',graphics_device_id=0 if images else -1,
                        headless=True,virtual_screen_capture=False,force_render=False)
    try:
        env.reset();contacts=[];palms=[];drifts=[];angles=[];states=[]
        ref_rot=Rotation.from_quat(rows[:,43:47]);pad_ids=env.force_handles.cpu().tolist()
        palm=env.gym.find_actor_rigid_body_index(env.envs[0],env.gym.find_actor_handle(env.envs[0],'hand'),'hand_r_base_link',gymapi.DOMAIN_ENV)
        for step in range(1,steps+1):
            env.step(env.zero_actions())
            state=env._collect_current_saved_states().cpu().numpy()
            if not np.isfinite(state).all():raise ValueError('Non-finite physical screen')
            drifts.append(np.linalg.norm(state[:,40:43]-rows[:,40:43],axis=1))
            angles.append((Rotation.from_quat(state[:,43:47])*ref_rot.inv()).magnitude())
            if step%RULES['contact_sample_control_steps']:continue
            contact=np.zeros((count,5),dtype=bool);palm_touch=np.zeros(count,dtype=bool)
            for i,handle in enumerate(env.envs):
                for c in env.gym.get_env_rigid_contacts(handle):
                    if float(c['lambda'])<=RULES['contact_force_threshold']:continue
                    pair={int(c['body0']),int(c['body1'])}
                    palm_touch[i]|=palm in pair and bool(pair & {env.object_link0_handle,env.object_link1_handle})
                    for f,pad in enumerate(pad_ids):
                        obj=env.object_link1_handle if f==0 else env.object_link0_handle
                        contact[i,f]|=pair=={int(pad),int(obj)}
            contacts.append(contact);palms.append(palm_touch);states.append(state)
        contacts=np.asarray(contacts);palms=np.asarray(palms);drifts=np.asarray(drifts);angles=np.asarray(angles)
        fractions=contacts.mean(0);palm_fractions=palms.mean(0)
        keep=(fractions.min(1)>=RULES['min_each_fingertip_contact_fraction']) & contacts[-1].all(1)
        keep&=palm_fractions<=RULES['max_palm_contact_fraction']
        keep&=(drifts.max(0)<=RULES['max_drift_m'])&(angles.max(0)<=RULES['max_rotation_rad'])
        keep&=np.stack([posture_mask(s) for s in states]).all(0)
        # Save the exact input state that was screened. Preserve original split
        # identities and avoid changing the grasp after the reachability test.
        for split in ('train','test'):
            (output/split).mkdir(exist_ok=True)
            np.save(output/split/'valid_grasps.npy',rows[keep&(data['splits']==split)])
        np.save(output/'valid_grasps.npy',rows[keep])
        (output/'valid').mkdir(exist_ok=True)
        np.save(output/'valid/valid_grasps.npy',rows[keep])
        np.save(output/'source_indices.npy',data['source_indices'][keep])
        save_json(output/'grasp_state_metadata.json',dict(pose_frame='hand_base',split_mode='original_train_test_preserved',filter_version=RULES['version']))
        save_json(output/'filter_validation.json',dict(rules=RULES,screened_sha256=digest(output/'screened.npz'),screening_sha256=digest(output/'screening.json'),
            physical_signature=physical_signature(),config=task_cfg,seed=20260920,steps=steps,contact_samples=len(contacts),
            physical_engine='ArtGrasp/PhysX, nominal paper friction 3, damping 1000, gravity, filtered hand collisions',
            count=count,valid=int(keep.sum()),train=int((keep&(data['splits']=='train')).sum()),test=int((keep&(data['splits']=='test')).sum()),
            accepted_source_indices=data['source_indices'][keep].tolist(),contact_fractions=fractions.tolist(),palm_contact_fractions=palm_fractions.tolist(),
            max_drift_m=drifts.max(0).tolist(),max_rotation_rad=angles.max(0).tolist(),
            outputs={name:digest(output/name) for name in ('valid_grasps.npy','valid/valid_grasps.npy','train/valid_grasps.npy','test/valid_grasps.npy','source_indices.npy')}))
        if images and keep.any():
            hand_rotation=Rotation.from_quat([env.hand_start_pose.r.x,env.hand_start_pose.r.y,env.hand_start_pose.r.z,env.hand_start_pose.r.w])
            hand_position=np.array([env.hand_start_pose.p.x,env.hand_start_pose.p.y,env.hand_start_pose.p.z])
            cam_position=hand_rotation.apply([.34,.13,.02])+hand_position
            cam_target=hand_rotation.apply([.035,.015,.1])+hand_position
            for handle,camera in zip(env.envs,env.cam_handle_list):
                env.gym.set_camera_location(camera,handle,gymapi.Vec3(*cam_position),gymapi.Vec3(*cam_target))
            env.gym.step_graphics(env.sim);env.gym.render_all_camera_sensors(env.sim)
            for index in np.flatnonzero(keep)[:4]:
                frame=env.gym.get_camera_image(env.sim,env.envs[index],env.cam_handle_list[index],gymapi.IMAGE_COLOR)
                Image.fromarray(frame.reshape(env.image_height,env.image_width,-1)[...,:3]).save(output/f'grasp-{int(data["source_indices"][index]):03d}.png')
        print(instance,'physical',int(keep.sum()),'/',count,'train',int((keep&(data['splits']=='train')).sum()),'test',int((keep&(data['splits']=='test')).sum()),flush=True)
    finally:env.gym.destroy_sim(env.sim)


def physical_signature():
    paths=[ROOT/p for p in ('isaacgymenvs/tasks/artgrasp.py','isaacgymenvs/tasks/artmanip.py','isaacgymenvs/tasks/base/vec_task.py')]
    return dict(implementation=implementation_digest(physical),files={str(p.relative_to(ROOT)):digest(p) for p in paths})


def check_dataset(require_test=True, minimum_train=10):
    """Verify provenance and exact subsets before the simulator can load them."""
    from scripts.validate_paper_grasps import check_dataset as check_source
    check_source(require_test=require_test)
    manifest=json.loads((ASSETS/'manifest.json').read_text())
    if manifest.get('grasp_filter',{}).get('rules')!=RULES:raise ValueError('Filtered asset manifest is stale')
    if (manifest['train_ids']!=[f'{i:03d}' for i in range(30)]
            or manifest['test_ids']!=[f'{i:03d}' for i in range(30,35)]):
        raise ValueError('Filtered geometry split must remain 000–029 / 030–034')
    reports=[]
    for instance in manifest['train_ids']+(manifest['test_ids'] if require_test else []):
        folder=TARGET/instance
        screen_report=json.loads((folder/'screening.json').read_text())
        report=json.loads((folder/'filter_validation.json').read_text())
        if screen_report['signature']!=input_signature(instance):raise ValueError(f'{instance}: stale screening inputs')
        if report['physical_signature']!=physical_signature() or report['rules']!=RULES:
            raise ValueError(f'{instance}: stale physical validation')
        if report['screening_sha256']!=digest(folder/'screening.json') or report['screened_sha256']!=digest(folder/'screened.npz'):
            raise ValueError(f'{instance}: screening changed after physical validation')
        for name,sha in report['outputs'].items():
            if digest(folder/name)!=sha:raise ValueError(f'{instance}/{name}: filtered output was changed')
        original=np.load(SOURCE/instance/'valid_grasps.npy',allow_pickle=False)
        ids=np.load(folder/'source_indices.npy',allow_pickle=False)
        rows=np.load(folder/'valid_grasps.npy',allow_pickle=False)
        if rows.shape!=(len(ids),75) or not np.isfinite(rows).all() or not len(rows):
            raise ValueError(f'{instance}: invalid or empty filtered cache')
        if len(set(ids.tolist()))!=len(ids) or not np.array_equal(rows,original[ids]) or not posture_mask(rows).all():
            raise ValueError(f'{instance}: source identity or posture check failed')
        if ids.tolist()!=report['accepted_source_indices']:raise ValueError(f'{instance}: accepted IDs changed')
        if not np.array_equal(rows,np.load(folder/'valid/valid_grasps.npy',allow_pickle=False)):
            raise ValueError(f'{instance}: full evaluation split differs')
        screened=np.load(folder/'screened.npz',allow_pickle=False)
        selected=np.isin(screened['source_indices'],ids)
        if (np.asarray(report['contact_fractions'])[selected].min()<RULES['min_each_fingertip_contact_fraction']
                or np.asarray(report['palm_contact_fractions'])[selected].max()>RULES['max_palm_contact_fraction']
                or np.asarray(report['max_drift_m'])[selected].max()>RULES['max_drift_m']
                or np.asarray(report['max_rotation_rad'])[selected].max()>RULES['max_rotation_rad']):
            raise ValueError(f'{instance}: accepted rows fail physical thresholds')
        splits=split_membership(rows,SOURCE/instance)
        for split in ('train','test'):
            subset=np.load(folder/split/'valid_grasps.npy',allow_pickle=False)
            if not np.array_equal(subset,rows[splits==split]) or len(subset)!=report[split]:
                raise ValueError(f'{instance}/{split}: split membership changed')
        if instance in manifest['train_ids'] and (report['train']<minimum_train or report['test']<1):
            raise ValueError(f'{instance}: insufficient independent train/test grasps')
        if json.loads((folder/'grasp_state_metadata.json').read_text())['pose_frame']!='hand_base':
            raise ValueError(f'{instance}: incorrect pose frame')
        reports.append(dict(instance=instance,original=len(original),posture=screen_report['posture_eligible'],
                            reachable=screen_report['reachable'],valid=len(rows),train=report['train'],test=report['test']))
    return reports


def dataset_totals(reports):
    totals={key:sum(r[key] for r in reports) for key in ('original','posture','reachable','valid')}
    totals['training_grasps']=sum(r['train'] for r in reports if int(r['instance'])<30)
    totals['test_grasps_on_training_geometry']=sum(r['test'] for r in reports if int(r['instance'])<30)
    totals['heldout_geometry_grasps']=sum(r['valid'] for r in reports if int(r['instance'])>=30)
    return totals


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','screen','physical','check']);p.add_argument('--instances',nargs='+',default=['000']);p.add_argument('--images',action='store_true');args=p.parse_args()
    if args.stage=='prepare':prepare();return
    if args.stage=='check':
        reports=check_dataset()
        save_json(TARGET/'dataset-report.json',dict(rules=RULES,instances=reports,
            totals=dataset_totals(reports)))
        print(json.dumps(reports,indent=2));return
    instances=[f'{i:03d}' for i in range(35)] if args.instances==['all'] else args.instances
    if args.stage=='physical' and len(instances)!=1:raise ValueError('Use a separate simulation process per instance')
    for instance in instances:
        if args.stage=='screen':screen(instance)
        else:physical(instance,args.images)


if __name__=='__main__':main()
