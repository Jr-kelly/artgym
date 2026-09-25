"""Prepare independent initial states using the existing physical-audit recipe."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics


def states_for_seed(source, seed, hand, trials=100):
    if trials < 1:
        raise ValueError('At least one initial state is required')
    rng = np.random.default_rng(seed)
    states = np.repeat(source, trials, axis=0)
    for state in states:
        delta = rng.uniform(-.01, .01, 20)
        state[:20] = np.clip(state[:20]+delta, hand.lower, hand.upper)
        state[20:40] = np.clip(state[20:40]+delta, hand.lower, hand.upper)
        translation = rng.uniform(-.5, .5, 3)/1000
        rotation = Rotation.from_rotvec(np.deg2rad(rng.uniform(-.5, .5, 3)))
        state[47:50] = state[40:43]+translation+rotation.apply(state[47:50]-state[40:43])
        state[40:43] += translation
        for start in [43, 50]:
            state[start:start+4] = (rotation*Rotation.from_quat(state[start:start+4])).as_quat()
        fk = hand.forward(state[:20])
        state[55:70] = np.concatenate([fk[n][:3, 3] for n in hand.config["track_links"]])
    return states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source_path = root/"caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy"
    source = np.load(source_path)
    assert source.shape == (1, 75)
    hand = WujiKinematics()
    reference = root/"runs/wuji-goal/verification/precision-near01-cp125-perturb-small/perturbed_initial_states.npy"
    # Match the exact float32 limits used by the original GPU environment.
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    assert np.array_equal(states_for_seed(source, 1616, hand), np.load(reference)), "Audit recipe mismatch"
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in args.seeds:
        p = args.output/("seed%d.npy" % seed)
        assert not p.exists()
        np.save(p, states_for_seed(source, seed, hand))
        rows.append(dict(seed=seed, path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    manifest = dict(reference_bitwise_equal=True, source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), rows=rows,
        scope="Same nominal grasp, new reset perturbations only. Position +/-0.5mm/axis, joints +/-0.01rad, rotation vector +/-0.5deg/axis.")
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
