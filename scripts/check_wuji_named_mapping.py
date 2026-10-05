import argparse,json,numpy as np
from pathlib import Path
from scripts.wuji_kinematics import WujiKinematics
from isaacgymenvs.deploy.wuji.joint_mapping import WujiJointMapping,SDK_NAMES
p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
h=WujiKinematics();m=WujiJointMapping(h.names);v=np.arange(20)+.125;sdk=m.to_sdk(v);assert np.array_equal(m.to_runtime(sdk),v)
assert sdk[3].tolist()==v[12:16].tolist() and sdk[4].tolist()==v[8:12].tolist()
z=np.load(a.trial/'trace.npz');samples=[]
for t in [16,18,20.1]:
 i=int(np.argmin(abs(z['time']-t)));q=z['q'][i];s=m.to_sdk(q);assert np.array_equal(s[3],q[12:16]) and np.array_equal(s[4],q[8:12]);samples.append(dict(time_s=float(z['time'][i]),measurement=m.record(q,'saved_simulation_encoder'),ring_rad=s[3].tolist(),pinky_rad=s[4].tolist()))
a.output.write_text(json.dumps(dict(runtime_names=h.names,sdk_names=SDK_NAMES,distinct_value_input=v.tolist(),distinct_value_sdk=sdk.tolist(),roundtrip_pass=True,sim_to_sdk_blocks=[int(m.sim_to_sdk[i*4]//4) for i in range(5)],sdk_to_sim_blocks=[int(m.sdk_to_sim[i*4]//4) for i in range(5)],actual_pose_checks=samples,physical_axes_zero_offsets_verified=False),indent=2))
