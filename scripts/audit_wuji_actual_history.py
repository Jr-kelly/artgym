"""Verify that actors never consume padded reset history in new training."""
from scripts.wuji_robust_learning import LearningSystem
import argparse,json
from pathlib import Path
import numpy as np,torch

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    system=LearningSystem(24,randomization_scale=0,loadmax=0,detentmax=0,delay=0,history_hold_frames=50)
    try:
        env=system.env;rows=[];calls=[];original=system.player.get_action
        def guarded(*args,**kwargs):
            counts=system.actual_history_count[system.policy_active]
            assert len(counts)>0 and int(counts.min())>=50
            calls.append(dict(control_step=len(rows),minimum_actual_frames=int(counts.min()),batch=len(counts)))
            return original(*args,**kwargs)
        system.player.get_action=guarded
        neutral=torch.zeros((24,20),device=env.device)
        for step in range(64):
            system.features();active=system.policy_active.clone();system.step(neutral)
            latest=env.proprioception_buf[:,-1].detach().cpu().numpy().copy()
            rows.append(dict(step=step,active=int(active.sum()),executed_max=float(env.actions[~active].abs().max()) if (~active).any() else 0.,frame=latest,counts=system.actual_history_count.detach().cpu().numpy().copy()))
        persistent=(system.actual_history_count>=64).nonzero(as_tuple=False).squeeze(-1)
        assert len(persistent)>0,'No uninterrupted episode available for history comparison'
        expected=np.stack([r['frame'] for r in rows[-50:]],axis=1)
        history=env.proprioception_buf.detach().cpu().numpy()
        error=float(np.max(np.abs(history[persistent.cpu().numpy()]-expected[persistent.cpu().numpy()])))
        report=dict(actor_calls=calls,first_actor_control_step=calls[0]['control_step'],actual_history_max_error=error,uninterrupted_episodes=len(persistent),holding_commands_max=max(r['executed_max'] for r in rows),passed=calls[0]['control_step']>=50 and error<1e-7 and max(r['executed_max'] for r in rows)<1e-7,scope='Actual-history compatibility proof; static proxy manipulation, no full demo')
        np.savez_compressed(a.output/'history.npz',actual=history,expected=expected,uninterrupted_envs=persistent.cpu().numpy())
        (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);assert report['passed']
    finally:system.close()
if __name__=='__main__':main()
