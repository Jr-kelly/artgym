"""Freeze the successful mixed estimator and generate an unfiltered 2x-reset stress cohort."""
from pathlib import Path
import datetime,hashlib,json,shutil
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics

def wider_states(source,seed,hand,trials=100,amplitude=2.):
 rng=np.random.default_rng(seed);states=np.repeat(source,trials,axis=0)
 for state in states:
  delta=rng.uniform(-.01*amplitude,.01*amplitude,20)
  state[:20]=np.clip(state[:20]+delta,hand.lower,hand.upper);state[20:40]=np.clip(state[20:40]+delta,hand.lower,hand.upper)
  translation=rng.uniform(-.5*amplitude,.5*amplitude,3)/1000
  rotation=Rotation.from_rotvec(np.deg2rad(rng.uniform(-.5*amplitude,.5*amplitude,3)))
  state[47:50]=state[40:43]+translation+rotation.apply(state[47:50]-state[40:43]);state[40:43]+=translation
  for start in [43,50]:state[start:start+4]=(rotation*Rotation.from_quat(state[start:start+4])).as_quat()
  fk=hand.forward(state[:20]);state[55:70]=np.concatenate([fk[n][:3,3] for n in hand.config['track_links']])
 return states

def main():
 r=Path(__file__).resolve().parents[1];g=r/'runs/wuji-goal';out=g/'rgb-wider300-total-seed20261123-v2';assert not out.exists()
 proposal=g/'rgb-wider-reset-stress-1932-proposal-v2.json';plan=json.loads(proposal.read_text());assert plan['seed']==20261123 and plan['amplitude']==2
 stats=json.loads((g/'diagnostics/rgb-independent-final-statistics-1802-v1.json').read_text());assert stats['passed_both_preregistered_clocks']['mixed']
 out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();candidate=plan['candidate'];p=r/candidate['path'];assert sha(p)==candidate['sha256'];shutil.copyfile(p,out/'mixed.pth');shutil.copyfile(p.with_suffix('.json'),out/'mixed.json')
 frozen=datetime.datetime.now(datetime.timezone.utc).isoformat();source=r/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy';base=np.load(source);assert base.shape==(3,75)
 hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
 assert np.array_equal(wider_states(base[:1],1616,hand,amplitude=1.),states_for_seed(base[:1],1616,hand)), '1x recipe must remain bitwise identical'
 old_paths=[g/'bridge3-evaluation-states/mixed332.npy',g/'rgb-fresh300-total-paired-seed20261120-v2/mixed332.npy',source];old=set()
 for p in old_paths:old.update(map(bytes,np.load(p)))
 pieces=[];groups=[]
 for index in range(3):
  seed=int(np.random.SeedSequence([plan['seed'],index]).generate_state(1)[0]);x=wider_states(base[index:index+1],seed,hand);assert np.isfinite(x).all() and len(np.unique(x,axis=0))==100 and not old.intersection(map(bytes,x));old.update(map(bytes,x));p=out/f'grasp{index}.npy';np.save(p,x);pieces.append(x);groups.append(dict(start=100*index,stop=100*(index+1),seed=seed,sha256=sha(p)))
 fourth=np.load(g/'bridge2-evaluation-states/heldout.npy');assert fourth.shape==(32,75);pieces.append(fourth);np.save(out/'mixed332.npy',np.concatenate(pieces))
 manifest=dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(),models_frozen=frozen,candidate=candidate,seed=plan['seed'],splits=groups,initial_states_sha256=sha(out/'mixed332.npy'),proposal_sha256=sha(proposal),physics_transitions=0,no_outcome_filter=True,perturbations=dict(position_per_axis_m=.001,joints_rad=.02,rotation_vector_component_deg=1.),old_cohorts_sha256={str(p.relative_to(r)):sha(p) for p in old_paths},fourth_reused_failure_control=True,one_x_recipe_bitwise_verified=True,source_sha256=sha(Path(__file__)),scope=plan['scope'])
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 prior=json.loads((g/'rgb-independent-paired-1729-v1-spec.json').read_text());prior.update(output='runs/wuji-goal/diagnostics/rgb-wider-reset-stress-1932-v2',wait_for='runs/wuji-goal/diagnostics/rgb-independent-paired-1729-v1',artifacts=dict(mixed=dict(path=str((out/'mixed.pth').relative_to(r)),sha256=candidate['sha256'])),initial_states=dict(path=str((out/'mixed332.npy').relative_to(r)),sha256=manifest['initial_states_sha256']),evaluation_seed=plan['seed'],scope=plan['scope'],preregistration=str(proposal.relative_to(r)),acceptance=plan['acceptance'])
 prior['stages']=[s for s in prior['stages'] if s['arm']=='mixed'];assert len(prior['stages'])==8
 sp=g/'rgb-wider-reset-stress-1932-v2-spec.json';sp.write_text(json.dumps(prior,indent=2)+'\n');print(json.dumps(dict(spec=str(sp),manifest=manifest)))
if __name__=='__main__':main()
