"""Strict transfer-only screening of immutable official Wuji grasp candidates.

Preserves official train/test identities. Reach is kinematic; subsequent physical
screen uses acquisition physics and exact rigid-body contact pairs for 2 s.
Neither gate certifies manipulation success. Original data remain unchanged.
"""
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.filter_wuji_fingertip_grasps import posture_mask,ThumbReach,split_membership,RULES
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'caches/initial_grasp/wuji/knife_wuji_official'
TARGET=ROOT/'caches/initial_grasp/wuji/knife_wuji_official_approved'
ASSETS=ROOT/'assets/objects/knife_wuji_official'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def knife_metadata(instance):
    urdf=ET.parse(ASSETS/instance/'mobility.urdf').getroot()
    joint=next(j for j in urdf.findall('joint') if j.get('type')=='prismatic')
    if not np.array_equal(np.fromstring(joint.find('axis').get('xyz'),sep=' '),[0,0,1]):
        raise ValueError('Unsupported slider axis')
    link=next(j for j in urdf.findall('link') if j.get('name')=='link_1')
    visual=link.find('visual');origin=visual.find('origin');jo=joint.find('origin')
    for item in [origin,jo]:
        if item is not None and np.linalg.norm(np.fromstring(item.get('rpy','0 0 0'),sep=' '))>1e-8:
            raise ValueError('Reach model requires axis-aligned primitives')
    position=sum((np.fromstring(item.get('xyz','0 0 0'),sep=' ') for item in [origin,jo] if item is not None),np.zeros(3))
    return dict(slider_origin=position.tolist(),slider_size=np.fromstring(visual.find('geometry/box').get('size'),sep=' ').tolist())


def screen(instance):
    source=SOURCE/instance;out=TARGET/instance;out.mkdir(parents=True,exist_ok=True)
    rows=np.load(source/'valid_grasps.npy');splits=split_membership(rows,source);ids=np.flatnonzero(posture_mask(rows))
    reach=ThumbReach();metadata=knife_metadata(instance);results=[];keep=[]
    for i in ids:
        result=reach.check(rows[i].astype(float),metadata);results.append(dict(source_index=int(i),**result))
        if result['passed']:keep.append(i)
    keep=np.asarray(keep,dtype=int)
    np.savez_compressed(out/'screened.npz',states=rows[keep],source_indices=keep,splits=splits[keep])
    record=dict(checked=now(),source_dataset='knife_wuji_official',instance=instance,original=len(rows),
        posture=len(ids),reachable=len(keep),train=int((splits[keep]=='train').sum()),test=int((splits[keep]=='test').sum()),
        source_sha256=sha(source/'valid_grasps.npy'),urdf_sha256=sha(ASSETS/instance/'mobility.urdf'),
        screened_sha256=sha(out/'screened.npz'),rules=RULES,reach_results=results,
        provenance='Official func_lygra/ArtGrasp output, filtered for user-approved thumbwards direction and full 40 mm reach')
    atomic_json(out/'screening.json',record);print(instance,'screened',record['posture'],record['reachable'],flush=True)


def physical(instance):
    import isaacgym
    from isaacgym import gymapi
    import torch
    from scripts.wuji_goal_common import configuration,make_env
    from omegaconf import OmegaConf
    from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
    source=SOURCE/instance;out=TARGET/instance;data=np.load(out/'screened.npz');rows=data['states'];count=len(rows)
    prior=json.loads((out/'screening.json').read_text())
    if prior['source_sha256']!=sha(source/'valid_grasps.npy') or prior['screened_sha256']!=sha(out/'screened.npz'):
        raise ValueError('Screened state provenance changed')
    if count==0:
        atomic_json(out/'filter_validation.json',dict(status='empty_after_reach',instance=instance,valid=0,train=0,test=0));return
    cfg=configuration('wuji_acquisition',count,['object=knife_wuji_acquisition',
        'object.asset.asset_root=assets/objects/knife_wuji_official',f"object.asset.instance_id_list=['{instance}']",
        'pipeline=cpu'],train='wujiAcquisitionSAPG',seed=20260926)
    env=make_env(cfg);tensor=torch.as_tensor(rows,device=env.device)
    env.sample_grasps=lambda ids:tensor[ids]
    original=env.compute_reward;captured={}
    def capture(actions):
        original(actions)
        captured.update(drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1).cpu().numpy(),
            rotation=(2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))).cpu().numpy(),
            position=env.object_pos.cpu().numpy().copy(),quaternion=env.object_rot.cpu().numpy().copy())
    env.compute_reward=capture
    try:
        env.reset();drifts=[];angles=[];postures=[];contacts=[];palms=[];reset=np.zeros(count,dtype=bool)
        pad_ids=env.force_handles.cpu().tolist()
        hand_actor=env.gym.find_actor_handle(env.envs[0],'hand')
        palm=env.gym.find_actor_rigid_body_index(env.envs[0],hand_actor,'hand_r_base_link',gymapi.DOMAIN_ENV)
        object_actor=env.object_handles[0]
        obj=[env.gym.find_actor_rigid_body_index(env.envs[0],object_actor,n,gymapi.DOMAIN_ENV) for n in ['link_0','link_1']]
        steps=round(2/(env.dt*env.control_freq_inv))
        for step in range(1,steps+1):
            _,_,done,_=env.step(torch.zeros((count,20),device=env.device));reset|=done.cpu().numpy().astype(bool)
            drifts.append(captured['drift']);angles.append(captured['rotation'])
            poses=rows.copy();poses[:,40:43]=captured['position'];poses[:,43:47]=captured['quaternion'];postures.append(posture_mask(poses))
            if step%3:continue
            env.gym.fetch_results(env.sim,True);contact=np.zeros((count,5),dtype=bool);palm_touch=np.zeros(count,dtype=bool)
            for i,handle in enumerate(env.envs):
                for c in env.gym.get_env_rigid_contacts(handle):
                    if float(c['lambda'])<=1e-6:continue
                    pair={int(c['body0']),int(c['body1'])}
                    palm_touch[i]|=palm in pair and bool(pair&set(obj))
                    for f,pad in enumerate(pad_ids):contact[i,f]|=pair=={int(pad),obj[1 if f==0 else 0]}
            contacts.append(contact);palms.append(palm_touch)
        fractions=np.mean(contacts,axis=0);palm_fraction=np.mean(palms,axis=0)
        max_drift=np.max(drifts,axis=0);max_rotation=np.max(angles,axis=0)
        keep=(fractions.min(1)>=.9)&np.asarray(contacts[-1]).all(1)&(palm_fraction==0)&(max_drift<=.01)&(max_rotation<=.25)&np.all(postures,axis=0)&~reset
        np.save(out/'valid_grasps.npy',rows[keep]);np.save(out/'source_indices.npy',data['source_indices'][keep])
        for split in ['train','test','valid']:
            (out/split).mkdir(exist_ok=True);mask=keep if split=='valid' else keep&(data['splits']==split)
            np.save(out/split/'valid_grasps.npy',rows[mask])
        atomic_json(out/'grasp_state_metadata.json',dict(pose_frame='hand_base',split_mode='original_train_test_preserved',filter_version='official_approved_acquisition_v1'))
        record=dict(status='completed',instance=instance,checked=now(),valid=int(keep.sum()),
            train=int((keep&(data['splits']=='train')).sum()),test=int((keep&(data['splits']=='test')).sum()),
            source_sha256=prior['source_sha256'],screened_sha256=sha(out/'screened.npz'),urdf_sha256=prior['urdf_sha256'],
            accepted_source_indices=data['source_indices'][keep].tolist(),rules=RULES,
            physical_protocol='Wuji acquisition physics: 2 seconds, 120 Hz simulation /30 Hz control, gravity, passive damping 0.3, hand friction1/object3, zero policy action',
            contact_fractions=fractions.tolist(),palm_contact_fractions=palm_fraction.tolist(),max_drift_m=max_drift.tolist(),
            max_rotation_rad=max_rotation.tolist(),any_reset=reset.tolist(),config=OmegaConf.to_container(cfg,resolve=True),
            outputs={name:sha(out/name) for name in ['valid_grasps.npy','source_indices.npy','train/valid_grasps.npy','test/valid_grasps.npy','valid/valid_grasps.npy']})
        atomic_json(out/'filter_validation.json',record);print(instance,'physical',record['valid'],'/',count,flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['screen','physical']);p.add_argument('--instance',required=True);a=p.parse_args()
    (screen if a.stage=='screen' else physical)(a.instance)
