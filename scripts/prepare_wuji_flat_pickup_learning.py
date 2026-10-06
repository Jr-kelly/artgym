"""Prepare exact issued motor prefix from real flat-table v19, never cached grasp."""
import json,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
p=Path('runs/flat-table-20261006/learning/real-prefix-v76');p.mkdir(parents=True,exist_ok=False);source=Path('runs/flat-table-20261006/development/middle-curl-v19/simulation/trace.npz');z=np.load(source);i=int(np.argmin(abs(z['time']-9.8)));targets=z['target'];assert targets.shape[1]==27
np.savez_compressed(p/'prefix.npz',targets=targets[:i+1],time=z['time'][:i+1],expected_object=z['object'][i],expected_arm=z['arm_q'][i],expected_q=z['q'][i])
k=G2Kinematics();arm=targets[i,:7].copy();W=k.forward(arm);path=[]
for t in np.arange(0,6+1/60,1/30):
 u=np.clip((t-1.5)/3,0,1);u=u**3*(10-15*u+6*u*u);M=W.copy();M[2,3]+=.16*u;arm,e=k.solve_near(M,arm);path.append(np.r_[arm,targets[i,7:]])
np.savez_compressed(p/'learn-path.npz',targets=np.array(path))
s=json.load(open('runs/newknife-20261005/batch/config/scene.json'));s.pop('initial_estimated_plans',None);s.pop('proprioceptive_pressure_spec',None);s['held_diagnostic']=False;s['initial_tabletop_placement']=dict(body_root_xy_m=[.37,-.5695],yaw_degrees=45,table_y_m=-.23);s.update(nominal_hand_friction=.8,nominal_knife_friction=1.8);(p/'scene.json').write_text(json.dumps(s,indent=2));j=dict(source=str(source),trace_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_end_time_s=float(z['time'][i]),prefix_frames=i+1,initial='whole-supported flat knife; actual motor approach/push/closure/partiallift replay',physical_resets='new training episode initialization only; none at learning takeover',actor='explicit30Hz sim_oracle relative knife pose+q+issued targets+phase; development only',action='27 arm/hand motor offsets, finite originalPD/limits/velocities/gravity',scope=__doc__);(p/'provenance.json').write_text(json.dumps(j,indent=2));print(json.dumps(j),flush=True)
