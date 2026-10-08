import json,unittest
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import convex_intersection_radius,exact_hand_knife_intersection

class OriginalMeshIntersectionRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/wuji_loaded_cap_sat_false_positive.json').read_text())
        cls.g=FunctionalEntryAffordance().g

    def test_inconclusive_sat_cannot_reject_clear_original_mesh(self):
        r=self.fixture
        self.assertLess(r['collision']['gap_lower_bound_m'],0.)
        proof=exact_hand_knife_intersection(self.g,np.array(r['hand_q']),np.array(r['wrist_in_knife']),r['slider_m'],r['collision'])
        self.assertTrue(proof['no_intersection'])
        self.assertLess(proof['exact_intersection_radius_m'],-.0002)

    def test_actual_positive_intersection_is_rejected(self):
        r=self.fixture;c=r['collision'];frame=np.array(r['wrist_in_knife'])@self.g.w.forward(r['hand_q'])[c['hand_link']]
        v=self.g.meshes[c['hand_link']][0][0];hand=v@frame[:3,:3].T+frame[:3,3]
        knife=next(p['vertices']for p in self.g.knife_geometry.collision_parts(r['slider_m'])if p['link']==c['knife_link']and p['index']==c['knife_component'])
        moved=hand-hand.mean(0)+knife.mean(0)
        self.assertGreater(convex_intersection_radius(moved,knife),.0001)

if __name__=='__main__':unittest.main()
