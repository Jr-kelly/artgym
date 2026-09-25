"""Freeze small one-axis knife geometry changes around the realistic anchor.

These are diagnostic near-neighbor geometries, not new optimized grasps or
paper-held-out shapes. Hold mass, slider dimensions, travel and physics fixed;
recompute box inertia. Thickness also moves the mounted slider onto the top
surface, with the same transform applied to its saved initial world position.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal'
    output = base/'geometry-sensitivity-20260922'
    assert not output.exists()
    original = root/'assets/objects/knife_wuji_demo_aligned'
    cache = root/'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000'
    source = cache/'train/valid_grasps.npy'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(source) == '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
    nominal = np.array([.019, .147, .008])
    definitions = [('nominal', nominal), ('length142', [.019, .142, .008]),
                   ('length152', [.019, .152, .008]), ('width18', [.018, .147, .008]),
                   ('width20', [.020, .147, .008]), ('body7', [.019, .147, .007]),
                   ('body9', [.019, .147, .009])]
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32); hand.upper = hand.upper.astype(np.float32)
    states = states_for_seed(np.load(source), 20261051, hand, trials=32)
    output.mkdir()
    np.save(output/'nominal-states.npy', states)
    records = {}
    for label, dimensions in definitions:
        dimensions = np.asarray(dimensions)
        name = 'knife_wuji_geometry_'+label+'_20260922'
        asset = root/'assets/objects'/name
        cached = root/'caches/initial_grasp/wuji'/name/'000'
        config = root/'isaacgymenvs/cfg/object'/(name+'.yaml')
        assert not asset.exists() and not cached.exists() and not config.exists()
        shutil.copytree(original, asset)
        shutil.copytree(cache, cached)
        tree = ET.parse(asset/'000/mobility.urdf')
        body = tree.find(".//link[@name='link_0']")
        for element in body.findall('./visual/geometry/box')+body.findall('./collision/geometry/box'):
            element.set('size', ' '.join('%.12g'%v for v in dimensions))
        mass = float(body.find('./inertial/mass').get('value'))
        inertia = mass/12 * (np.sum(dimensions**2)-dimensions**2)
        for name_i, value in zip(['ixx','iyy','izz'], inertia):
            body.find('./inertial/inertia').set(name_i, repr(float(value)))
        delta_z = float((dimensions[2]-nominal[2])/2)
        origin = tree.find(".//joint[@name='slider']/origin")
        xyz = np.fromstring(origin.get('xyz'), sep=' '); xyz[2] += delta_z
        origin.set('xyz', ' '.join(repr(v) for v in xyz))
        # Maintain the visual-only blade in the same body-relative plane.
        blade = tree.find(".//link[@name='link_1']/visual/origin")
        blade_xyz = np.fromstring(blade.get('xyz'), sep=' '); blade_xyz[2] -= delta_z
        blade.set('xyz', ' '.join(repr(v) for v in blade_xyz))
        if label == 'nominal':
            # Exact copied source baseline, including URDF formatting.
            assert delta_z == 0
        else:
            tree.write(asset/'000/mobility.urdf', encoding='utf-8', xml_declaration=True)
        (asset/'lbx.json').write_text(json.dumps({'000':dimensions.tolist()+[.01,.03,.003]},indent=2)+'\n')
        def transform(a):
            result=a.copy()
            result[:,47:50] += Rotation.from_quat(a[:,43:47]).apply(np.tile([0.,0.,delta_z],(len(a),1)))
            return result
        for file in cached.rglob('*.npy'):
            a=np.load(file)
            if a.ndim==2 and a.shape[1]==75:
                np.save(file,transform(a))
        variant_states=transform(states)
        state_path=output/(label+'-states.npy')
        if label!='nominal':np.save(state_path,variant_states)
        assert np.array_equal(variant_states[:,:47],states[:,:47])
        assert np.array_equal(variant_states[:,50:],states[:,50:])
        config.write_text('defaults:\n  - knife_wuji_precision_near01\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000']\n")
        parameters=dict(label=label,handle_size=dimensions.tolist(),slider_size=[.01,.03,.003],
            total_size_lwt=[float(dimensions[1]),float(dimensions[0]),float(dimensions[2]+.003)],
            slider_origin=xyz.tolist(),masses=[.029,.006],travel=.05,slider_mount_shift_z=delta_z,
            scope=__doc__,visual_only_blade=True,hardware_calibrated=False)
        (asset/'000/parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
        records[label]=dict(object=name,parameters=parameters,states=str(state_path.relative_to(root)),
            states_sha256=sha(state_path),urdf_sha256=sha(asset/'000/mobility.urdf'),
            artifact_sha256={str(p.relative_to(root)):sha(p) for parent in [asset,cached] for p in parent.rglob('*') if p.is_file()})
    manifest=dict(scope=__doc__,seed=20261051,nominal_grasps=1,perturbations_per_geometry=32,
        protocol='Same hand/body initialization, derived slider mount transform, no result-based filtering. Only 2 s commands for initial diagnosis.',
        source_sha256={str(p.relative_to(root)):sha(p) for p in [source,original/'000/mobility.urdf',Path(__file__)]},variants=records)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    checkpoint='runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    jobs=[]
    for mode in ['correct', 'observation_only', 'static']:
        for label,_ in definitions:
            if mode=='observation_only' and label=='nominal':continue
            jobs.append(dict(name='geometry-near5cp50-'+label+'-'+mode+'-seed51-timed2seconds',
                module='scripts.audit_wuji_geometry_sensitivity',checkpoint=checkpoint,
                args=['--variant',label,'--geometry-mode',mode,'--stage-seconds','2']))
    (base/'audit-queue-geometry-sensitivity.json').write_text(json.dumps(jobs,indent=2)+'\n')
    (base/'geometry-sensitivity-proposal.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(variants=7,nominal_grasps=1,perturbations=32,queue_jobs=len(jobs))))


if __name__=='__main__':main()
