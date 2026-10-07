"""Add bounded velocity lead to motor targets under the original native PD.

This keeps the simulator's damping, effort, collisions and joint limits intact.
The lead uses planned joint velocity, never native contact force as an input.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--motor',type=Path,required=True)
    p.add_argument('--physics',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-lead-rad',type=float,default=.07);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    motion=json.loads(a.motor.read_text());physics=json.loads(a.physics.read_text())
    rows=motion['rows'];D=motion['diagnostics'];times=np.array([r['time_s'] for r in rows])
    assert len(rows)==len(D) and np.allclose(times,[r['time_s'] for r in D])
    q=np.array([r['planned_hand_q'] for r in D]);v=np.gradient(q,times,axis=0)
    kp=np.array(physics['kp'])[7:27];kd=np.array(physics['kd'])[7:27]
    lead=np.clip(v*kd/kp,-a.max_lead_rad,a.max_lead_rad);h=WujiKinematics()
    for row,offset in zip(rows,lead):
        base=np.array(row['hand_q'])
        command=np.clip(base+offset,np.minimum(base,h.lower+.02),np.maximum(base,h.upper-.02))
        row['hand_q']=command.tolist()
        row['planned_velocity_lead_rad']=(command-base).tolist()
    motion['damping_feedforward']=dict(source_motor=str(a.motor),source_motor_sha256=hashlib.sha256(a.motor.read_bytes()).hexdigest(),
        source_physics=str(a.physics),source_physics_sha256=hashlib.sha256(a.physics.read_bytes()).hexdigest(),
        original_kd=kd.tolist(),original_kp=kp.tolist(),max_lead_rad=a.max_lead_rad,
        observed_max_lead_rad=float(abs(lead).max()),scope=__doc__)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(motion,indent=2))
    record('direct_bounded_damping_feedforward_prepared',[str(a.output)],config=motion['damping_feedforward'],
           next_step='One nativefunctionalcontacttransfer checks actualcarrier load andslidercontact; no claimfrom plannedvelocity compensation alone')
    print(json.dumps(motion['damping_feedforward']))


if __name__=='__main__':main()
