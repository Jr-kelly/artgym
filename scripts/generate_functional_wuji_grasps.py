"""Generate Wuji functional grasps with the public Lightning Grasp engine.

Uses Lightning Grasp (Zhao-Heng Yin, CC BY-NC 4.0) contact fields, wrench search,
GPU IK and collision filtering. Local adaptation implements ArtManip's category
contact-region template: thumb on slider, other fingertips on handle.
Run with the separate CUDA 12 Lightning Grasp Python, NOT Isaac Gym Python.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

ROOT = Path(__file__).resolve().parents[1]


def candidate_key(q, pose):
    return (tuple(np.round(q/.01).astype(int))
            + tuple(np.round(pose[:3, 3]/.001).astype(int))
            + tuple(np.round(Rotation.from_matrix(pose[:3, :3]).as_rotvec()/.01).astype(int)))


def atomic_array(path, value):
    temporary = path.with_suffix('.npy.tmp')
    with temporary.open('wb') as stream:
        np.save(stream, value)
    os.replace(temporary, path)


def field_signature(urdf, config, samples, seed):
    """Invalidate cached fields when geometry, limits or patch rules change."""
    digest = hashlib.sha256(urdf.read_bytes())
    digest.update(json.dumps(config, sort_keys=True, default=lambda x: x.tolist()).encode())
    digest.update(f'{samples}:{seed}'.encode())
    for mesh in sorted({e.attrib['filename'] for e in ET.parse(urdf).iter('mesh')}):
        digest.update((urdf.parent/mesh).read_bytes())
    return digest.hexdigest()[:16]


def functional_projection_mesh(urdf, tree, config):
    """Keep IK refinement on allowed pad faces (upstream ignores its rule)."""
    from lygra.mesh import RobotMesh
    robot_mesh = RobotMesh(urdf)
    vertices, faces, normals, vi, fi = [], [], [], [0], [0]
    for name in tree.get_all_link_names():
        mesh = robot_mesh.get_link_collision_mesh(name)
        keep = np.ones(len(mesh.faces), dtype=bool)
        for direction, threshold in config['movable_link'].get(name, {}).get('disabled_normal', []):
            keep &= (mesh.face_normals @ direction) <= np.cos(threshold)
        vertices.append(mesh.vertices)
        faces.append(mesh.faces[keep])
        normals.append(mesh.face_normals[keep])
        vi.append(vi[-1]+len(mesh.vertices))
        fi.append(fi[-1]+int(keep.sum()))
        if name in config['movable_link'] and not keep.any():
            raise ValueError(f'No allowed contact faces on {name}')
    return dict(v=np.concatenate(vertices), f=np.concatenate(faces), n=np.concatenate(normals),
                vi=np.array(vi), fi=np.array(fi))


def sample_box(size, center, count, rng):
    """Uniform-area sampling with exact face normals and no surface reconstruction."""
    size, center = np.asarray(size), np.asarray(center)
    area = np.array([size[1]*size[2], size[0]*size[2], size[0]*size[1]])
    axis = rng.choice(3, count, p=area/area.sum())
    sign = rng.choice([-1., 1.], count)
    points = rng.uniform(-.5, .5, (count, 3))*size
    points[np.arange(count), axis] = sign*size[axis]/2
    normals = np.zeros((count, 3)); normals[np.arange(count), axis] = sign
    return points+center, normals


def object_points(meta, rng, count=2048):
    hp, hn = sample_box(meta['handle_size'], [0, 0, 0], count, rng)
    sp, sn = sample_box(meta['slider_size'], meta['slider_initial_center'], count//2, rng)
    # Remove top-face handle contacts inside the entire slider travel corridor.
    width = meta['slider_size'][0]/2 + .001
    start = meta['slider_initial_center'][2]-meta['slider_size'][2]/2-.001
    stop = meta['slider_initial_center'][2]+.05+meta['slider_size'][2]/2+.001
    forbidden = (hn[:, 1]>.5)&(np.abs(hp[:, 0])<width)&(hp[:, 2]>start)&(hp[:, 2]<stop)
    hp, hn = hp[~forbidden], hn[~forbidden]
    relative = sp-np.asarray(meta['slider_initial_center'])
    thumb = (sn[:, 1]>.5)&(np.abs(relative[:, 0])<meta['slider_size'][0]/2-.001)&(np.abs(relative[:, 2])<meta['slider_size'][2]/2-.001)
    sp, sn = sp[thumb], sn[thumb]
    points, normals = np.concatenate([hp, sp]), np.concatenate([hn, sn])
    labels = np.r_[np.zeros(len(hp), dtype=int), np.ones(len(sp), dtype=int)]
    # Full surfaces are used for collision checking, including forbidden regions.
    ap, _ = sample_box(meta['handle_size'], [0,0,0], count, rng)
    bp, _ = sample_box(meta['slider_size'], meta['slider_initial_center'], count//2, rng)
    return points, normals, labels, np.concatenate([ap,bp])


def make_robot():
    from lygra.robot.base import RobotInterface
    cfg = yaml.safe_load((ROOT/'isaacgymenvs/cfg/hand/wuji.yaml').read_text())
    class Wuji(RobotInterface):
        def get_default_urdf_path(self): return str(ROOT/cfg['asset'])
        def get_active_joints(self): return cfg['dof_names']
        def get_base_link(self): return 'hand_r_base_link'
        def get_static_links(self): return ['hand_r_base_link']
        def get_mesh_scale(self): return 1.
        def get_canonical_space(self): return np.array([.02,-.025,.065]), np.array([.06,.025,.115])
        def get_contact_field_config(self):
            return dict(type='v1', movable_link={name: {'disabled_normal':[(np.array([-1.,0,0]),np.pi*.51)]} for name in cfg['force_links']},
                        static_link={'hand_r_base_link': {'allowed_normal':[(np.array([1.,0,0]),np.pi*.25)]}})
    return Wuji(), cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lygra-root', type=Path, default=ROOT/'tmp/lightning-grasp')
    p.add_argument('--asset-dir', default='knife_wuji_paper')
    p.add_argument('--instances', nargs='+', default=['000'])
    p.add_argument('--count', type=int, default=1000)
    p.add_argument('--outer', type=int, default=128)
    p.add_argument('--inner', type=int, default=64)
    p.add_argument('--field-samples', type=int, default=80000)
    p.add_argument('--max-batches', type=int, default=1000)
    p.add_argument('--seed', type=int, default=20260920)
    args = p.parse_args()
    sys.path.insert(0, str(args.lygra_root.resolve()))
    import torch
    from lygra import gem, lbvh
    if gem is None or lbvh is None: raise RuntimeError('Lightning Grasp CUDA extensions failed to load')
    from lygra.kinematics import build_kinematics_tree
    from lygra.contact_field import build_contact_field
    from lygra.mesh import get_urdf_mesh_decomposed
    from lygra.memory import IKGPUBufferPool
    from lygra.pipeline.module.object_placement import sample_object_pose, get_object_pose_sampling_args
    from lygra.pipeline.module.contact_query import batch_object_all_contact_fields_interaction
    from lygra.pipeline.module.contact_collection import sample_from_mask_and_gather
    from lygra.pipeline.module.contact_optimization import search_contact_point
    from lygra.pipeline.module.kinematics import batch_ik, batch_contact_adjustment
    from lygra.pipeline.module.postprocess import batch_assign_free_finger_and_filter

    torch.manual_seed(args.seed); np.random.seed(args.seed)
    torch.set_num_threads(4)
    robot, cfg = make_robot()
    tree = build_kinematics_tree(robot.urdf_path, active_joint_names=robot.get_active_joints())
    projection_mesh = functional_projection_mesh(robot.urdf_path, tree, robot.get_contact_field_config())
    mesh = get_urdf_mesh_decomposed(robot.urdf_path, tree)
    static_mesh = get_urdf_mesh_decomposed(robot.urdf_path, tree, override_link_names=robot.get_static_links())
    # Exclude mechanically adjacent/overlapping links in the same finger only.
    names = tree.get_all_link_names()
    whitelist = []
    for a in names:
        for b in names:
            if a==b: continue
            same_digit = any(f'_{f}_' in a and f'_{f}_' in b for f in ('thumb','index','middle','ring','pinky'))
            adjacent_palm = ('base_link' in a and b.endswith(('link1','link2'))) or ('base_link' in b and a.endswith(('link1','link2')))
            if same_digit or adjacent_palm: whitelist.append([a,b])
    pairs = tree.get_self_collision_check_link_pairs(link_body_id=mesh['link_body_id'], whitelist_link=[], whitelist_pairs=whitelist)
    pairs = torch.as_tensor(pairs, device='cuda', dtype=torch.int32)
    signature = field_signature(ROOT/cfg['asset'], robot.get_contact_field_config(), args.field_samples, args.seed)
    cache = ROOT/'tmp/paper-grasps'/f'wuji-field-{signature}.pkl'
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        with cache.open('rb') as f: field = pickle.load(f)
    else:
        field = build_contact_field(robot.urdf_path, robot.get_contact_field_config(), patch_pos_dist_tol=.0075)
        field.generate_contact_field(tree, n_iter=args.field_samples)
        with cache.open('wb') as f: pickle.dump(field, f)
    accel = field.generate_acceleration_structure(method='lbvhs2')
    parent_ids = torch.tensor([tree.get_link_id(n) for n in field.get_all_parent_link_names()], device='cuda')
    links = field.get_all_contact_link_names()
    assert set(links)==set(cfg['force_links']), links
    pool = IKGPUBufferPool(tree.n_dof(), tree.n_link(), n_actuated_dof=tree.n_actuated_dof(),
                          max_batch=args.outer*args.inner, retry=10)
    folder = ROOT/'assets/objects'/args.asset_dir
    instances = sorted(x.name for x in folder.iterdir() if x.is_dir()) if args.instances==['all'] else args.instances
    for instance in instances:
        started = time.time(); rng = np.random.default_rng(args.seed+int(instance))
        meta = json.loads((folder/instance/'parameters.json').read_text())
        output = ROOT/'caches/initial_grasp/wuji'/args.asset_dir/instance
        output.mkdir(parents=True, exist_ok=True)
        if (output/'candidate_manifest.json').exists():
            old = json.loads((output/'candidate_manifest.json').read_text())
            if (old.get('unique_candidates',0)>=args.count
                    and old.get('hand_field_signature') == signature
                    and old.get('urdf_sha256') == meta['urdf_sha256']):
                print('Already generated',instance,flush=True); continue
        torch.manual_seed(args.seed+int(instance)); np.random.seed(args.seed+int(instance))
        q_all, pose_all, seen = [], [], set()
        for iteration in range(args.max_batches):
            points, normals, labels, all_points = object_points(meta, rng)
            points = torch.as_tensor(points, device='cuda', dtype=torch.float32)
            normals = torch.as_tensor(normals, device='cuda', dtype=torch.float32)
            all_points = torch.as_tensor(all_points, device='cuda', dtype=torch.float32)
            labels = torch.as_tensor(labels, device='cuda')
            with torch.no_grad():
                poses, condition = sample_object_pose(args.outer, points, normals, field, tree, static_mesh,
                                                      get_object_pose_sampling_args('canonical',robot))
                # Upstream sampler can return more than requested; pool is bounded.
                poses = poses[:args.outer]
                condition = {k:v[:args.outer] for k,v in condition.items()}
                interactions = batch_object_all_contact_fields_interaction(points, normals, poses, accel)
                for patch, name in enumerate(field.get_all_parent_link_names()):
                    allowed = labels==(1 if 'thumb' in name else 0)
                    interactions[:,patch,~allowed] = -1
                active = (interactions>=0).int()
                by_link = field.reduce_link_interaction(active)
                # Require all five functional fingers; never silently reduce contact count.
                keep = torch.where((by_link.sum(-1)>5).all(-1))[0]
                if not len(keep):
                    print(instance,iteration,'no five-finger contact domains',flush=True); continue
                domains, domain_ids = sample_from_mask_and_gather(by_link[keep],torch.cat([points,normals],-1),128)
                link_ids = torch.arange(5,device='cuda').expand(len(keep),-1)
                cond = {k:v[keep] for k,v in condition.items()}
                pos, normal, obj_ids, obj_poses, contact_links, outer_ids = search_contact_point(
                    domains[...,:3], domains[...,3:], domain_ids, poses[keep], link_ids,
                    batch_size=args.inner, condition=cond, zo_step=5, zo_lr=.003)
                if not len(pos):
                    print(instance,iteration,'no wrench-feasible contacts',flush=True); continue
                contact_ids, local_ids = field.sample_contact_ids(active[keep],interactions[keep],outer_ids,contact_links,obj_ids)
                cp, cn = field.sample_contact_geometry(contact_ids,local_ids)
                result = batch_ik(tree,contact_ids,parent_ids,cp.float(),cn.float(),pos.float(),normal.float(),obj_poses.float(),pool)
                coarse_count = len(result['q'])
                if not coarse_count:
                    print(instance,iteration,'no IK solutions',flush=True); continue
                result = batch_contact_adjustment(tree,projection_mesh,result['q'],result['q_mask'],
                    result['contact_link_id'],result['contact_link_id'],result['contact_pos'],result['contact_normal'],
                    result['target_pos'],result['target_normal'],result['object_pose'],pool,n_iter=5)
                if result is None or not len(result['q']): continue
                fine_count = len(result['q'])
                result = batch_assign_free_finger_and_filter(tree,result,all_points,pairs,mesh)
                for q, pose in zip(result['q'].cpu().numpy(),result['object_pose'].cpu().numpy()):
                    key = candidate_key(q, pose)
                    if key in seen: continue
                    seen.add(key);q_all.append(q.copy());pose_all.append(pose.copy())
                    if len(q_all)>=args.count:break
            print(instance,iteration,'coarse',coarse_count,'fine',fine_count,'unique',len(q_all),flush=True)
            if q_all:
                atomic_array(output/'qpos.npy',np.asarray(q_all,dtype=np.float32))
                atomic_array(output/'opos.npy',np.asarray(pose_all,dtype=np.float32))
            if len(q_all)>=args.count: break
        manifest = dict(instance=instance,unique_candidates=len(q_all),requested=args.count,seconds=time.time()-started,
                        engine='Lightning Grasp af43818e864b0389c97b73429e5e60de2a2de593',
                        contact_template='thumb slider +y with margin; four fingertips handle excluding swept slider',
                        self_collision_filter='cross-digit and distal-to-palm GJK; adjacent/same-digit pairs excluded',
                        urdf_sha256=meta['urdf_sha256'],seed=args.seed+int(instance),field_samples=args.field_samples,
                        hand_field_signature=signature, dof_names=cfg['dof_names'])
        (output/'candidate_manifest.json').write_text(json.dumps(manifest,indent=2))
        if len(q_all)<args.count: raise RuntimeError(f'{instance}: only {len(q_all)}/{args.count} candidates; see generation log')


if __name__=='__main__':
    main()
