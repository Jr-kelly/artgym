"""Check complete collected sequences and publish explicit episode/time identity."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 entries=[];B=R/'runs/unified-policy-20260930'
 for sec in [2,5]:
  for source in range(4):
   p=B/f'train-data-t{sec}'/f'source{source}';info=json.loads((p/'interface.json').read_text());report=json.loads((p/'report.json').read_text());expert=B/'experts'/('historical.pth' if source<3 else 'source3.pth')
   with np.load(p/'sequences.npz') as z:s={k:z[k] for k in z.files}
   with np.load(p/'trace.npz') as z:t={k:z[k] for k in z.files}
   assert s['obs'].shape==(600,128,138);active=s['active_before'].astype(bool);continuing=active[1:]&~s['done'][:-1].astype(bool)
   checks=dict(finite=all(np.isfinite(x).all() for x in s.values()),executed_clip_mu_max=float(abs(s['executed_action']-np.clip(s['mu'],-1,1))[active].max()),previous_action_max=float(abs(s['previous_action'][1:]-s['executed_action'][:-1])[continuing].max()),previous_action_obs_max=float(abs(s['obs'][:,:,75:95]-s['previous_action'])[active].max()),target_physics_max=float(abs(s['target_clipped']-t['target'])[active].max()),zero_initial_previous_action_max=float(abs(s['previous_action'][0]).max()),sapg_id_min=float(s['obs'][:,:,137].min()),sapg_id_max=float(s['obs'][:,:,137].max()))
   assert checks['finite'] and all(checks[k]<1e-6 for k in ['executed_clip_mu_max','previous_action_max','previous_action_obs_max','target_physics_max','zero_initial_previous_action_max']),checks
   assert checks['sapg_id_min']==checks['sapg_id_max']==50
   assert sha(expert)==info['checkpoint_sha256']==report['checkpoint_sha256']
   states=R/f'research/unified-policy-20260930/data/train-source{source}.npy';assert sha(states)==report['initial_states_sha256']
   entries.append(dict(source=source,seconds=sec,path=str(p.relative_to(R)),sequence_sha256=sha(p/'sequences.npz'),trace_sha256=sha(p/'trace.npz'),expert_sha256=sha(expert),states_path=str(states.relative_to(R)),states_sha256=sha(states),episodes=128,control_steps=76800,valid_label_steps=int(active.sum()),strict_successes=report['stable_full_all_endpoints'],checks=checks,action_clipping_fraction=float((abs(s['mu'][active])>1).mean()),joint_target_clipping_fraction=float((abs(s['target_unclipped'][active]-s['target_clipped'][active])>1e-7).mean())))
 result=dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,entries=entries,physics_episodes=1024,control_steps=614400,fit_episode_indices=list(range(96)),validation_episode_indices=list(range(96,128)),sequence_axes=['control_step0..599','episode0..127','feature'],observation_slices=dict(policy=[0,111],privileged=[111,132],critic_contact_proxy=[132,137],sapg_coefficient_id=[137,138]),timing='obs/mu/executed/previous targets pre-action; trace physical state post-action pre-reset; done returned after transition; step0 RNN zero then clear only when previous transition done',scope='Assigned experts only during data collection; no source ID supplied to actor; all outcomes retained; fit excludes inactive labels, evaluation excludes no initial states')
 out=R/'research/unified-policy-20260930/dataset-audit.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,entries=len(entries),physics_episodes=1024,control_steps=614400)))
if __name__=='__main__':main()
