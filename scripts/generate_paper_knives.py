"""Generate articulated knives with ArtManip's method and fixed train/test IDs.

This is a local reimplementation because the authors' make_data submodule is
unavailable. Geometry follows the published ranges; joint placement/contact
templates are explicitly recorded local choices, not recovered author assets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from scripts.build_wuji_knife_demo import box_link
from scripts.wuji_kinematics import ROOT


PROFILES = {
    'paper': {
        'handle_lower': [.015, .008, .100], 'handle_upper': [.040, .020, .160],
        'slider_lower': [.007, .002, .020], 'slider_upper': [.015, .008, .035],
        'description': 'Full independent uniform distribution in ArtManip Table 6',
    },
    'slim_utility': {
        'handle_lower': [.023, .009, .145], 'handle_upper': [.029, .013, .160],
        'slider_lower': [.009, .002, .020], 'slider_upper': [.013, .004, .028],
        'description': 'Provisional compact utility knife proportions requested by user; not a measured product',
        'nominal_handle': [.026, .011, .152], 'nominal_slider': [.011, .003, .024],
    },
    'nt_a300gr': {
        'handle_lower': [.0175, .008, .140], 'handle_upper': [.0205, .010, .154],
        'slider_lower': [.009, .002, .027], 'slider_upper': [.011, .0035, .033],
        'description': 'NT A-300GR/GRP reference envelope with local geometric variation',
        'nominal_handle': [.019, .008, .147], 'nominal_slider': [.010, .003, .030],
        'nominal_total_size_lwt_m': [.147, .019, .011], 'nominal_total_mass_kg': .035,
        'link_masses_kg': [.029, .006],
        'dimensions_source': 'https://www.tanomail.com/product/1181883/',
        'mechanism_source': 'https://www.ntcutter.co.jp/en/products/detail/312',
        'assumptions': ['8 mm handle + 3 mm raised slider approximates the published 11 mm overall thickness',
                        'slider 30 x 10 mm footprint estimated from manufacturer photo, not a dimensioned drawing',
                        '29 g handle + 6 g moving assembly is an estimated allocation of the published 35 g total',
                        '50 mm joint travel is the paper task range, not a verified product limit',
                        'ratchet/auto-lock remains a one-joint effective-resistance approximation pending calibration'],
    },
}


def generate(output, seed=20260920, profile='nt_a300gr'):
    rng = np.random.default_rng(seed)
    output.mkdir(parents=True, exist_ok=True)
    boxes, instances = {}, []
    dimensions = PROFILES[profile]
    for index in range(35):
        name = f'{index:03d}'
        folder = output / name
        folder.mkdir(exist_ok=True)
        handle = rng.uniform(dimensions['handle_lower'], dimensions['handle_upper'])
        slider = rng.uniform(dimensions['slider_lower'], dimensions['slider_upper'])
        # Anchor instance is the explicit provisional physical target.
        if index == 0 and 'nominal_handle' in dimensions:
            handle = np.array(dimensions['nominal_handle'])
            slider = np.array(dimensions['nominal_slider'])
        lower = float(rng.uniform(-.055, -.0175))
        upper = lower + .05
        # x = width, y = thickness, z = handle length. Exposed slider on +y.
        # At the lower limit the slider is inside the handle's longitudinal span.
        start_z = -handle[2] * .15
        origin = [0., float((handle[1] + slider[1]) / 2), float(start_z-lower)]
        robot = ET.Element('robot', name='artmanip_knife_'+name)
        masses = dimensions.get('link_masses_kg', [.04, .01])
        box_link(robot, 'link_0', handle.tolist(), masses[0], '.58 .60 .64 1')
        box_link(robot, 'link_1', slider.tolist(), masses[1], '.12 .13 .15 1')
        joint = ET.SubElement(robot, 'joint', name='slider', type='prismatic')
        ET.SubElement(joint, 'parent', link='link_0')
        ET.SubElement(joint, 'child', link='link_1')
        ET.SubElement(joint, 'origin', xyz=' '.join(map(str, origin)))
        ET.SubElement(joint, 'axis', xyz='0 0 1')
        ET.SubElement(joint, 'limit', lower=str(lower), upper=str(upper), effort='100', velocity='1')
        ET.SubElement(joint, 'dynamics', damping='1000', friction='0.001')
        ET.ElementTree(robot).write(folder/'mobility.urdf', encoding='utf-8', xml_declaration=True)
        boxes[name] = handle.tolist()+slider.tolist()
        metadata = dict(id=name, split='train' if index<30 else 'test', geometry_profile=profile, handle_size=handle.tolist(),
                        masses=masses, total_size_lwt=[float(handle[2]),float(handle[0]),float(handle[1]+slider[1])],
                        slider_size=slider.tolist(), joint_lower=lower, joint_upper=upper,
                        slider_origin=origin, slider_initial_center=[0., origin[1], float(start_z)],
                        urdf_sha256=hashlib.sha256((folder/'mobility.urdf').read_bytes()).hexdigest())
        (folder/'parameters.json').write_text(json.dumps(metadata, indent=2))
        instances.append(metadata)
    (output/'lbx.json').write_text(json.dumps(boxes, indent=2))
    manifest = dict(seed=seed, source='https://arxiv.org/html/2609.12498v1#A3.SS1',
                    geometry_profile=profile, dimension_distribution=dimensions, units='metres',
                    axes=['width', 'thickness', 'length'], real_object_calibrated=False,
                    implementation='Local Table 6 reimplementation; author make_data inaccessible',
                    contact_template={'thumb': 'exposed slider +y face; 1 mm edge margin',
                                      'other_fingertips': 'handle surface, excluding slider swept volume'},
                    train_ids=[i['id'] for i in instances if i['split']=='train'],
                    test_ids=[i['id'] for i in instances if i['split']=='test'], instances=instances)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Generated 30 training and 5 held-out Knife assets:', output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'assets/objects/knife_wuji_paper')
    parser.add_argument('--seed', type=int, default=20260920)
    parser.add_argument('--profile', choices=PROFILES, default='nt_a300gr')
    args = parser.parse_args()
    generate(args.output, args.seed, args.profile)


if __name__ == '__main__':
    main()
