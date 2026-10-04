"""Export measured joints/issued targets from an actual simulated controller run.

Trace truth is used only to locate the recorded joint arrays and audit source
provenance. The exported replay NPZ contains exactly four legal fields.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--motor-plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--takeover-seconds',type=float,default=5.)
    p.add_argument('--prefix-start-seconds',type=float,help='Include earlier measured/issued prefix for stateful legal pressure adapters; no object/contact fields')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    t=np.load(a.trial/'trace.npz');physics=json.loads((a.trial/'physics.json').read_text())
    start=round(a.takeover_seconds*30)-50
    if a.prefix_start_seconds is not None:
        start=round(a.prefix_start_seconds*30)
        assert start<=round(a.takeover_seconds*30)-50
    assert start>=1 and abs(a.takeover_seconds*30-round(a.takeover_seconds*30))<1e-7
    clock=np.arange(len(t['time']))/30.
    # Native trace time/arm_q are frame end; observed_q is precommand.
    arm=np.roll(t['arm_q'],1,axis=0)
    np.savez_compressed(a.output/'legal-input.npz',clock_s=clock[start:],
        hand_measured_q=t['observed_q'][start:],arm_measured_q=arm[start:],
        issued_hand_target=t['target'][start:,physics['hand_indices']])
    plan=json.loads(a.motor_plan.read_text());estimate=plan['initial_geometry_estimate']
    (a.output/'estimate.json').write_text(json.dumps(estimate,indent=2))
    (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2))
    receipt=dict(scope='Recorded simulation measured/issued arrays only; no hardware data or current object/contact/load replay input',
        control_clock='Frame beginning; arm_q preceding completed row; observed_q already precommand',
        learned_takeover_seconds=a.takeover_seconds,control_frames=len(clock[start:]),
        trace_sha256=hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),
        motor_plan_sha256=hashlib.sha256(a.motor_plan.read_bytes()).hexdigest(),
        legal_input_sha256=hashlib.sha256((a.output/'legal-input.npz').read_bytes()).hexdigest(),
        source_joint_names=physics['robot_dof_names'],hand_indices=physics['hand_indices'],arm_indices=physics['arm_indices'])
    (a.output/'export-receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))

if __name__=='__main__':main()
