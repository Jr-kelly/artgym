"""Static no-policy holding diagnostic; failure records are retained by source.
This is neither fitting nor manipulation evaluation.
"""
from scripts.wuji_robust_learning import LearningSystem
import argparse,json,numpy as np,torch
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=192);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    system=LearningSystem(a.envs,seed=2026100310,randomization_scale=.5,loadmax=.1,detentmax=.1,delay=0);env=system.env
    # Capture before automatic reset, retaining each first static attempt.
    original=env.compute_reward;frames=[]
    def record(action):
        original(action);frames.append(dict(object=env.object_pose.detach().cpu().numpy().copy(),initial=env.init_object_pos.detach().cpu().numpy().copy(),initial_rot=env.init_object_rot.detach().cpu().numpy().copy(),contact=env.contact_info.detach().cpu().numpy().copy(),q=env.hand_dof_pos.detach().cpu().numpy().copy(),reset=env.reset_buf.detach().cpu().numpy().copy(),time=env.progress_buf.detach().cpu().numpy().copy()))
    env.compute_reward=record
    try:
        # Held target action0; the actor is never run and policy success cannot filter.
        for _ in range(60):env.step(torch.zeros((a.envs,20),device=env.device))
        trace={k:np.stack([f[k] for f in frames]) for k in frames[0]};np.savez_compressed(a.output/'trace.npz',**trace)
        rows=[]
        for i in range(a.envs):
            first_reset=np.flatnonzero(trace['reset'][:,i]);stop=int(first_reset[0])+1 if len(first_reset) else 60
            drift=np.linalg.norm(trace['object'][:stop,i,:3]-trace['initial'][:stop,i],axis=1)
            rows.append(dict(env=i,instance=env.instance_id_list[i%len(env.instance_id_list)],first_attempt_steps=stop,held60=stop==60 and not len(first_reset),max_drift_m=float(drift.max()),thumb_contact_fraction=float(trace['contact'][:stop,i,0].mean()),support_count_mean=float(trace['contact'][:stop,i,1:].sum(1).mean()),scope='Static zero-action physically perturbed holding, not policy-selected or operation'))
        report=dict(n=a.envs,held60=sum(r['held60'] for r in rows),records=rows,scope='Proxy functional grasp validity diagnosis; no tabletop handover claim')
        (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    finally:system.close()
if __name__=='__main__':main()
