"""Measure episode-local live B travel/hold, separately from action acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.g2_kinematics import transform
from scripts.g2_knife_geometry import KnifeGeometry


def evaluate(directory):
    directory = Path(directory)
    trace_path = directory / 'trace.npz'
    z = np.load(trace_path)
    entry = json.loads((directory / 'retained-push-entry.json').read_text())
    args = json.loads((directory / 'plan.json').read_text())['args']
    recorded = args.get('recorded_handoff') is not None
    initialization = json.loads((directory/'recorded-initialization.json').read_text()) if recorded else {}
    ideal = initialization.get('initializer_category') == 'ideal-diagnostic'
    motor_path = args.get('recorded_support_command') or args.get('flat_table_prefix')
    if motor_path is None:
        raise ValueError('No actual live-skill episode configuration')
    motor = json.loads(Path(motor_path).read_text())
    knife = KnifeGeometry(motor['retained_push_skill']['knife_spec'])
    elapsed = z['time'] - z['time'][0] + 1 / 30
    intake_time = float(entry['time_s'])
    push = elapsed >= intake_time
    delta = z['slider'] - float(entry['slider_start_m'])
    clearances = []
    for o, slider in zip(z['object'], z['slider']):
        O = transform(o[:3], o[3:7])
        v = np.concatenate([p['vertices'] for p in knife.collision_parts(float(slider))])
        clearances.append(float((v @ O[:3, :3].T + O[:3, 3])[:, 2].min() - .75))
    # A hold is a consecutive interval in this episode, measured against its
    # actual live takeover slider value. Whole-knife clearance is independent.
    valid = push & (delta > .020) & (np.array(clearances) > .002)
    run = longest = 0
    for v in valid:
        run = run + 1 if v else 0
        longest = max(longest, run)
    last_second = elapsed >= elapsed[-1] - 1 + 1e-7
    calls = [json.loads(line) for line in (directory / 'retained-push-call.jsonl').open()]
    result = dict(
        trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        actor_sha256=entry['actor_sha256'],
        intake_time_s=intake_time,
        intake_slider_q_m=float(entry['slider_start_m']),
        active_max_m=float(delta[push].max()),
        final_second_min_active_m=float(delta[last_second].min()),
        continuous_over20mm_clear_hold_s=longest / 30,
        minimum_whole_knife_clearance_m=min(clearances),
        minimum_push_whole_knife_clearance_m=float(np.array(clearances)[push].min()),
        history_frames=entry['history_frames'],
        full_B_commands=sum(c['phase'] == 'retained-push' for c in calls),
        displacement_and_clearance_pass=longest >= 30,
        full_table_acceptance=False,
        same_episode_fresh_table_route=not recorded,
        initializer_category='ideal-diagnostic' if ideal else 'recorded-actual' if recorded else 'fresh-table',
        scope=('Declared ideal-initial-state independent physical diagnosis; thumbposture/motor assignedonlyatINITIALIZATION, not reachedbyregrasp. ' if ideal else 'Independent recorded-state live adapter development diagnosis; missing exact robot velocities and contact cache. '
               if recorded else 'Fresh table episode travel/clearance measurement; contact, limits, action and full-video acceptance still separate. ')+
              'Displacement '
              'belongs only to this physical episode; geometry/action/video '
              'and native contact checks remain separate.')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    a = p.parse_args()
    result = evaluate(a.directory)
    (a.directory / 'live-intake-result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
