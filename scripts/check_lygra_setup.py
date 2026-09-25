"""Check the isolated Lightning Grasp runtime; optionally fix urdfpy's NumPy alias."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fix-urdfpy-numpy', action='store_true')
    args = parser.parse_args()
    import torch
    import urdfpy.urdf
    path = Path(urdfpy.urdf.__file__)
    if args.fix_urdfpy_numpy:
        source = path.read_text()
        if '.astype(np.float)' in source:
            path.write_text(source.replace('.astype(np.float)', '.astype(float)'))
            print('Fixed urdfpy 0.0.22 obsolete NumPy alias in', path)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root/'tmp/lightning-grasp'))
    import lygra
    if lygra.gem is None or lygra.lbvh is None:
        raise RuntimeError('Lightning Grasp CUDA kernels did not load')
    print('torch:', torch.__version__, 'CUDA:', torch.version.cuda, 'GPU:', torch.cuda.get_device_name())
    print('Lightning Grasp CUDA modules loaded')
    from lygra.kinematics import build_kinematics_tree, batch_fk
    from scripts.wuji_kinematics import WujiKinematics
    import numpy as np
    hand = WujiKinematics()
    tree = build_kinematics_tree(str(root/hand.config['asset']), active_joint_names=hand.names)
    rng = np.random.default_rng(20260920)
    q = rng.uniform(hand.lower, hand.upper, (16,20)).astype(np.float32)
    matrices = batch_fk(tree, torch.from_numpy(q).cuda())['link'].cpu().numpy()
    error = 0.
    for index, values in enumerate(q):
        reference = hand.forward(values)
        for name in hand.config['track_links']:
            actual = matrices[index,tree.get_link_id(name)]
            np.testing.assert_allclose(actual, reference[name], atol=1e-6)
            error = max(error, float(np.abs(actual-reference[name]).max()))
    print('Wuji Lightning Grasp FK/joint-order parity passed, maximum matrix error:', error)


if __name__ == '__main__':
    main()
