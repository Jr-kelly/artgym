"""Separate closing failure modes and measured thumb tracking, before any intervention."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.wuji_kinematics import WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root/'runs/wuji-goal/verification/precision-near01-cp50-perturb-small'
    report = json.loads((folder/'report.json').read_text())
    trace = np.load(folder/'trace.npz')
    hand = WujiKinematics()
    assert hand.names[17] == 'hand_r_thumb_joint2'
    rows = []
    for i, row in enumerate(report['records']):
        mask = trace['active'][:, i]
        events = np.flatnonzero(trace['stage_event'][:, i]*mask)
        category = 'success' if row['cycles'] >= 1 else 'close_failure' if len(events) else 'open_failure'
        if not len(events):
            rows.append(dict(env=i, category=category)); continue
        start = int(events[0])+1
        end = int(events[1])+1 if len(events)>1 else int(np.flatnonzero(mask)[-1])+1
        slider = trace['slider'][start:end, i]
        target = trace['target'][start:end, i, 17]
        actual = trace['q'][start:end, i, 17]
        near = np.abs(slider) < .002
        longest = max((len(x) for x in ''.join('1' if b else '0' for b in near).split('0')), default=0)
        early_end = min(30, len(actual))
        rows.append(dict(env=i, category=category, open_time_sec=start/30,
            close_time_window_sec=(end-start)/30, minimum_close_position_mm=float(slider.min()*1000),
            maximum_close_dwell_sec=longest/30, final_slider_mm=float(slider[-1]*1000),
            thumb_joint2_mean_tracking_error_rad=float(np.abs(target-actual).mean()),
            thumb_joint2_early_tracking_error_rad=float(np.abs(target[:early_end]-actual[:early_end]).mean()),
            thumb_joint2_target_limit_fraction=float((np.minimum(target-hand.lower[17],hand.upper[17]-target)<.001).mean()),
            termination=row['completion_reason']))
    failures = [row for row in rows if row['category']=='close_failure']
    result = dict(source_checkpoint_sha256=report['checkpoint_sha256'],
        source_report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),
        source_trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest(), rows=rows,
        closing_failures=len(failures), never_enter_close_tolerance=sum(r['maximum_close_dwell_sec']==0 for r in failures),
        insufficient_close_dwell=sum(0<r['maximum_close_dwell_sec']<.3 for r in failures),
        interpretation='Target saturation and large tracking error occur during many failures, but early errors also occur in successful trials. This is a testable intervention hypothesis, not proof of a root cause. No actuator torque was measured by this trace.')
    target = root/'runs/wuji-goal/diagnostics/precision-near01-closing-tracking.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))


if __name__=='__main__':
    main()
