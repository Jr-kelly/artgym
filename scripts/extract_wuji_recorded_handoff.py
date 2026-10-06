"""Extract actual recorded takeover and short continuation; never restore simulator state.
Measured velocity channels remain exact. Missing robot velocities are explicitly
labelled finite-difference estimates, unsuitable as proof of exact restoration.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def extract(source,output,takeover_elapsed=46.,continuation_s=1.):
 source=Path(source);output=Path(output)
 if output.exists():raise FileExistsError(output)
 z=np.load(source,allow_pickle=False);clock=z['time'].astype(float);elapsed=clock-clock[0]+1/30
 if takeover_elapsed<elapsed[0] or takeover_elapsed>elapsed[-1]:raise ValueError('Takeover outside recorded interval')
 index=int(np.argmin(abs(elapsed-takeover_elapsed)));end=int(np.searchsorted(elapsed,elapsed[index]+continuation_s,side='right'))
 q=np.concatenate([z['arm_q'],z['q']],axis=1);velocity=np.gradient(q,clock,axis=0)
 output.mkdir(parents=True)
 selected={name:z[name][index:end] for name in z.files if z[name].ndim and z[name].shape[0]==len(clock)}
 selected['elapsed_s']=elapsed[index:end];selected['estimated_robot_velocity']=velocity[index:end]
 np.savez_compressed(output/'recorded-continuation.npz',**selected)
 np.savez_compressed(output/'takeover.npz',object_state=z['object'][index],robot_q=q[index],estimated_robot_velocity=velocity[index],slider_q=z['slider'][index],slider_velocity=z['slider_velocity'][index],issued_target=z['applied_target'][index],issued_target_history=z['applied_target'][:index+1],elapsed_history_s=elapsed[:index+1])
 manifest=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),takeover_index=index,takeover_elapsed_s=float(elapsed[index]),available_continuation_s=float(elapsed[min(end,len(clock))-1]-elapsed[index]),frames=end-index,pose_source='recorded sim_oracle',exact_recorded_channels=['object pose and linear/angular velocity','robot positions','slider position and velocity','issued motor targets and full prior target history'],estimated_channels=['robot velocity: finite difference of recorded 30Hz positions'],missing_for_exact_simulator_resume=['raw robot velocities','PhysX solver/contact warm-start cache','internal controller state not recorded in trace'],scope='Offline recorded actual-state development input; no simulator setters, no new task success, no exact restore claim')
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--takeover-elapsed',type=float,default=46.);p.add_argument('--continuation-s',type=float,default=1.);a=p.parse_args()
 if a.continuation_s<=0:raise ValueError('Positive continuation required')
 print(json.dumps(extract(a.source,a.output,a.takeover_elapsed,a.continuation_s),indent=2))
if __name__=='__main__':main()
