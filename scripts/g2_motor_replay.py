"""Motor-only replay of an independently scored successful local trajectory.

This is an open-loop diagnostic baseline, not live teacher/student inference.
Never contains object poses to inject. Offsets are anchored once to the actual
handoff motor reference; original joint limits and command slew are mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


class MotorReplay:
    def __init__(self, path, actual_targets, lower, upper):
        self.plan = json.loads(Path(path).read_text())
        self.offsets = np.asarray(self.plan['hand_target_offsets_rad'], dtype=np.float32)
        assert self.offsets.shape == (600,20)
        self.initial = np.asarray(actual_targets,dtype=np.float32).copy()
        self.lower, self.upper = np.asarray(lower), np.asarray(upper)
        self.previous = self.initial.copy()
        self.index = 0
        steps = np.diff(np.vstack([np.zeros((1,20)), self.offsets]),axis=0)
        assert np.max(np.abs(steps[:,:16])) < .020002
        assert np.max(np.abs(steps[:,16:])) < .025002
        intended = self.initial+self.offsets
        assert np.all(intended >= self.lower-1e-6) and np.all(intended <= self.upper+1e-6)

    def step(self):
        assert self.index < len(self.offsets)
        target = self.initial+self.offsets[self.index]
        self.last_increment = target-self.previous
        self.previous = target.copy()
        self.index += 1
        return target.copy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--score',type=Path,required=True)
    p.add_argument('--replica',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    initial_path = Path(__file__).resolve().parents[1]/'configs/g2_local/S-actual-state.npz'
    initial = np.load(initial_path)
    t = np.load(a.trace)
    score = json.loads(a.score.read_text())['episodes'][a.replica]
    assert score['success'] and score['complete'] and len(t['time']) == 600
    offsets = t['reference_targets'][:,a.replica,7:27]-initial['reference_targets'][7:27]
    steps = np.diff(np.vstack([np.zeros((1,20)),offsets]),axis=0)
    plan = dict(method='open-loop replay of learned motor commands; not online teacher/student',
        source_trace=str(a.trace.resolve()),source_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),
        source_replica=a.replica,independent_source_score=score,
        reset_source_sha256=hashlib.sha256(initial_path.read_bytes()).hexdigest(),
        hand_order='index,middle,pinky,ring,thumb;4 joints each',
        seconds=20,control_hz=30,reversal_seconds=5,slider_goals_m=[.04,0,.04,0],
        reference='actual motor targets fixed once at takeover; no physical pose substitution',
        support_step_max_rad=float(np.max(np.abs(steps[:,:16]))),
        thumb_step_max_rad=float(np.max(np.abs(steps[:,16:]))),
        hand_target_offsets_rad=offsets.tolist())
    a.output.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='hand_target_offsets_rad'}))


if __name__ == '__main__':main()
