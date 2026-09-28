"""Freeze physically qualified novel base grasps without loading any policy result."""
import argparse,datetime,hashlib,json
from pathlib import Path
import numpy as np
from scripts.reference_metrics import unique_grasp_indices
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--states',type=Path,required=True);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--static',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 states=np.load(a.states);geometry=json.loads(a.geometry.read_text());assert geometry['states_sha256']==sha(a.states)
 report=json.loads((a.static/'report.json').read_text());assert report['control_mode']=='static_initial_targets' and report['initial_states_sha256']==sha(a.states)
 trace=np.load(a.static/'trace.npz');assert trace['active'].shape==(600,len(states))
 assert report['initial_state_rows']==list(range(len(states)))
 records=[];eligible=[]
 for i,g in enumerate(geometry['records']):
  assert g['row']==i
  valid=trace['active'][:,i]&~trace['fall'][:,i]&~trace['invalid'][:,i]
  body=(trace['drift'][:,i]<.01)&(trace['rotation'][:,i]<.25)
  # Sensor order is thumb,index,middle,ring,pinky. Ignore no frames.
  support=(trace['contact'][:,i,1:]>0).sum(-1)
  contact_fraction=float((support>=3).mean())
  gates=dict(posture=g['posture'],thumb_path=g['reach']['passed'],not_old_family=not g['old_near_duplicates'],alive_full=bool(valid.all()),body_stable=bool(body.all()),support_contact=contact_fraction>=.95)
  qualified=all(gates.values());records.append(dict(row=i,gates=gates,contact_fraction=contact_fraction,qualified_before_new_dedup=qualified))
  if qualified:eligible.append(i)
 kept=[eligible[j] for j in unique_grasp_indices(states[eligible],20)] if eligible else []
 np.save(a.output/'base.npy',states[kept]);hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
 perturbed=np.concatenate([states_for_seed(states[i:i+1],a.seed+i,hand,trials=32) for i in kept]) if kept else np.empty((0,75),dtype=states.dtype)
 np.save(a.output/'perturb32.npy',perturbed)
 manifest=dict(status='frozen' if kept else 'no_qualified_new_grasps',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_states_sha256=sha(a.states),geometry_sha256=sha(a.geometry),static_trace_sha256=sha(a.static/'trace.npz'),source_rows=kept,base_grasp_count=len(kept),trials_per_grasp=32,perturbation_seed=a.seed,records=records,artifact_sha256={n:sha(a.output/n) for n in ['base.npy','perturb32.npy']},selection='physical gates only; neither trained checkpoint nor policy outcomes loaded',scope='base grasps physically screened; perturbations unfiltered until paired static validation; never training or CP selection')
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='records'}))
if __name__=='__main__':main()
