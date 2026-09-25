"""Training-only preload selection and separately frozen held-out validation.

Initial measured joints and object states stay unchanged. Only commanded joint
targets move the five pad contact points inward along their current outward
surface normals. These are simulator initialization probes, not RL trajectories
or measured force commands, and they are not sent to hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.wuji_kinematics import FINGERS, WujiKinematics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selection", type=Path,
        help="Frozen selection from the completed training probe, required for five held-out rows.")
    args = parser.parse_args()
    validation = args.selection is not None
    expected_split = "test" if validation else "train"
    if args.source.parent.name != expected_split:
        raise ValueError("The source split does not match training-probe or held-out validation mode")
    args.output.mkdir(parents=True, exist_ok=True)
    states = np.load(args.source)
    assert states.shape == (5 if validation else 33, 75) and np.isfinite(states).all()
    hand = WujiKinematics()
    offsets = [0., .5, 1., 2., 4.]
    if validation:
        selection = json.loads(args.selection.read_text())
        if selection["status"] != "selected_on_training_only":
            raise ValueError("The training-only selection must be frozen before validation")
        offsets = [selection["selected_offset_mm"]]
    targets, records = [], []
    for offset_mm in offsets:
        for i, source in enumerate(states):
            state = source.copy()
            start = source[20:40].astype(np.float64)
            q = start.copy()
            points, normals = hand.contacts(start)
            errors = []
            for finger_index, finger in enumerate(FINGERS):
                if offset_mm:
                    q, _ = hand.solve_finger(finger, points[finger_index]+offset_mm/1000*normals[finger_index],
                                            q, normal=normals[finger_index])
                    q = np.clip(q, np.maximum(hand.lower, start-.15), np.minimum(hand.upper, start+.15))
                actual = hand.contacts(q)[0][finger_index]
                errors.append(float(np.linalg.norm(actual-(points[finger_index]+offset_mm/1000*normals[finger_index]))))
            state[20:40] = q
            assert np.array_equal(state[:20], source[:20]) and np.array_equal(state[40:], source[40:])
            targets.append(state)
            row = dict(env=len(records), requested_preload_mm=offset_mm,
                max_target_shift_rad=float(np.max(abs(q-start))), residual_per_pad_m=errors)
            row["validation_row" if validation else "train_row"] = i
            records.append(row)
        print(json.dumps(dict(offset_mm=offset_mm, prepared=len(targets))), flush=True)
    out = np.stack(targets)
    np.save(args.output/"initial_states.npy", out)
    result = dict(scope=__doc__, source=str(args.source),
        source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        states_sha256=hashlib.sha256((args.output/"initial_states.npy").read_bytes()).hexdigest(),
        cap_rad=.15, offsets_mm=offsets, records=records,
        split=expected_split,
        selection_sha256=hashlib.sha256(args.selection.read_bytes()).hexdigest() if validation else None,
        selection_rule=("Fixed training-selected offset; report all five validation rows without reselection."
                        if validation else "Use training rows only: maximize stable20s count, then minimum preload. "
                        "Do not remove failed rows. Any later held-out validation must be separate."))
    (args.output/"manifest.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
