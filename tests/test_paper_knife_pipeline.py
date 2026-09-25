"""Checks against paper ranges, held-out separation and functional contact rules."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np
import yaml

from scripts.generate_paper_knives import generate
from scripts.generate_functional_wuji_grasps import object_points

ROOT = Path(__file__).resolve().parents[1]


class PaperKnifePipelineTests(unittest.TestCase):
    def test_assets_and_functional_regions(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest = generate(directory, profile='paper')
            self.assertEqual(len(manifest['train_ids']), 30)
            self.assertEqual(len(manifest['test_ids']), 5)
            self.assertFalse(set(manifest['train_ids']) & set(manifest['test_ids']))
            config = yaml.safe_load((ROOT/'isaacgymenvs/cfg/object/knife_wuji_paper.yaml').read_text())
            self.assertEqual(config['asset']['instance_id_list'], manifest['train_ids'])
            rng = np.random.default_rng(41)
            for item in manifest['instances']:
                path = directory/item['id']/'mobility.urdf'
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['urdf_sha256'])
                tree = ET.parse(path)
                sizes = [np.fromstring(e.get('size'), sep=' ') for e in tree.findall('link/collision/geometry/box')]
                self.assertTrue(np.all((sizes[0] >= [.015,.008,.10]) & (sizes[0] <= [.04,.02,.16])))
                self.assertTrue(np.all((sizes[1] >= [.007,.002,.020]) & (sizes[1] <= [.015,.008,.035])))
                joint = tree.find('joint')
                self.assertEqual(joint.get('type'), 'prismatic')
                lower, upper = map(float, (joint.find('limit').get('lower'), joint.find('limit').get('upper')))
                self.assertAlmostEqual(upper-lower, .05)
                self.assertLessEqual(lower, -.0175)
                self.assertGreaterEqual(lower, -.055)
                start = np.fromstring(joint.find('origin').get('xyz'), sep=' ') + [0,0,lower]
                np.testing.assert_allclose(start, item['slider_initial_center'])
                # The full 40 mm goal must remain within the modeled joint travel.
                self.assertLessEqual(lower+.04, upper)
                points, normals, labels, collision_points = object_points(item, rng, 4096)
                self.assertTrue((labels==0).any() and (labels==1).any())
                slider_contacts = points[labels==1] - start
                np.testing.assert_allclose(normals[labels==1], np.tile([0,1,0], (len(slider_contacts),1)))
                self.assertTrue(np.all(np.abs(slider_contacts[:,0]) < sizes[1][0]/2-.001))
                self.assertTrue(np.all(np.abs(slider_contacts[:,2]) < sizes[1][2]/2-.001))
                handle_points = points[labels==0]
                top = normals[labels==0,1] > .5
                corridor = ((np.abs(handle_points[:,0]) < sizes[1][0]/2+.001)
                            & (handle_points[:,2] > start[2]-sizes[1][2]/2-.001)
                            & (handle_points[:,2] < start[2]+.05+sizes[1][2]/2+.001))
                self.assertFalse((top & corridor).any())
                self.assertTrue(np.isfinite(collision_points).all())

    def test_slim_target_and_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = generate(Path(temp), profile='slim_utility')
            self.assertFalse(manifest['real_object_calibrated'])
            np.testing.assert_allclose(manifest['instances'][0]['handle_size'], [.026,.011,.152])
            for item in manifest['instances']:
                w,t,l = item['handle_size']
                self.assertTrue(.023 <= w <= .029 and .009 <= t <= .013 and .145 <= l <= .16)
                self.assertLess(t/w, .57)
                self.assertGreater(l/w, 5)

    def test_sourced_reference_envelope_and_mass(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = generate(Path(temp))
            self.assertEqual(manifest['geometry_profile'], 'nt_a300gr')
            anchor = manifest['instances'][0]
            np.testing.assert_allclose(anchor['total_size_lwt'], [.147,.019,.011])
            self.assertAlmostEqual(sum(anchor['masses']), .035)
            tree = ET.parse(Path(temp)/'000/mobility.urdf')
            sizes = [np.fromstring(e.get('size'), sep=' ') for e in tree.findall('link/collision/geometry/box')]
            joint = tree.find('joint')
            origin = np.fromstring(joint.find('origin').get('xyz'), sep=' ')
            origin += [0,0,float(joint.find('limit').get('lower'))]
            minimum = np.minimum(-sizes[0]/2, origin-sizes[1]/2)
            maximum = np.maximum(sizes[0]/2, origin+sizes[1]/2)
            np.testing.assert_allclose((maximum-minimum)[[2,0,1]], [.147,.019,.011])
            masses = [float(e.get('value')) for e in tree.findall('link/inertial/mass')]
            self.assertAlmostEqual(sum(masses), .035)
            self.assertTrue(manifest['dimension_distribution']['dimensions_source'].startswith('https://'))
            self.assertFalse(manifest['real_object_calibrated'])


if __name__ == '__main__':
    unittest.main()
