"""Learning begins after entire actual flat-to-held v104 physical replay, never ideal state reset."""
import json,hashlib,numpy as np
from pathlib import Path
p=Path('runs/flat-table-20261006/learning/acquired-handoff-v121');p.mkdir(parents=True);source=Path('runs/flat-table-20261006/development/clamped-extraction-v104/simulation/trace.npz');z=np.load(source);i=int(np.argmin(abs(z['time']+1/30)));np.savez_compressed(p/'prefix.npz',targets=z['applied_target'][:i+1],time=z['time'][:i+1],expected_object=z['object'][i],expected_arm=z['arm_q'][i],expected_q=z['q'][i]);motor=z['applied_target'][i].copy();plan=json.load(open('runs/flat-table-20261006/preparation/acquired-middle-link4-v107/candidate.json'));path=[]
for t in np.arange(0,9+1/60,1/30):
 # Train new support establishment first. Thumb stays clamped throughout; no mandatory wrist lift or thumb release.
 u=np.clip((t-2)/4,0,1);u=u**3*(10-15*u+6*u*u);M=motor.copy();M[11:15]=motor[11:15]*(1-u)+np.array(plan['middle_q'])*u;path.append(M)
np.savez_compressed(p/'learn-path.npz',targets=np.array(path));s=json.load(open('runs/flat-table-20261006/learning/real-prefix-v76/scene.json'));(p/'scene.json').write_text(json.dumps(s,indent=2));(p/'provenance.json').write_text(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),frames=i+1,physical_initial='wholeflat supported45deg',takeover='actual bilateral capclamp wholeheld no stage statesetters',phase='supportestablishment before thumbrelease',not_old_failed_partialpickup=True),indent=2));print(i+1,motor.shape)
