"""Correlated full-motor short-course search in actual native physics.

Saved motor paths are training candidates, never independent validation.
All motor spans and pausable phase remain the existing v2 contract.
"""
import argparse, json, time, signal, hashlib
from pathlib import Path
import isaacgym
import torch
import numpy as np
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_conjugate
from scripts.wuji_regrasp_learning import RegraspLearning
from scripts.record_wuji_flat_table_event import record
from scripts.check_wuji_action_quality import HandIntersection


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True);p.add_argument('--reference',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--generations',type=int,default=60)
    p.add_argument('--seconds',type=float,default=4.)
    p.add_argument('--resume',type=Path)
    p.add_argument('--robust',action='store_true',help='16 paired candidates; rank by worse actual outcome under mild initial-state perturbation')
    p.add_argument('--clear-planning-cache',action='store_true');p.add_argument('--functional-intake',action='store_true',help='Prefer actual thumb-pad / slider surface approach while carrying; exact original pose remains a soft prior')
    p.add_argument('--hand-motor-span',type=float,default=.6,help='Motor command offset authority; physical original limits and slew remain unchanged')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.manual_seed(20261008749)
    cfg=dict(source=a.source,reference=a.reference,seconds=a.seconds,environments=32,
             knots=4,action='All27 motor offsets and pausable phase; linear temporal correlation',
             objective='Final1s native carrying and relative intake proximity; no phase completion reward',
             scope='Recorded actual initialization / native training fitting; no B or fulltable acceptance',
             source_sha256=hashlib.sha256(Path(a.source,'takeover.npz').read_bytes()).hexdigest(),
             reference_sha256=hashlib.sha256(Path(a.reference).read_bytes()).hexdigest())
    cfg['clear_planning_cache']=a.clear_planning_cache
    cfg['robust_paired_candidates']=a.robust
    cfg['robust_comparison']='Fixedcommon nominal plusone boundedperturbation for everycandidate/generation; warmstartcache stillnotexactrestore'
    cfg['functional_intake']=a.functional_intake
    cfg['hand_motor_span_rad']=a.hand_motor_span
    (a.output/'config.json').write_text(json.dumps(cfg,indent=2))
    record('correlated_full_motor_course_started',[str(a.output/'config.json')],cfg,
           updates={'add_active_jobs':[str(a.output)]},next_step='Select actual sustained-bearing candidate; independent native and B tests required')
    stop=[False];signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True))
    e=None
    try:
        e=RegraspLearning(32,a.source,a.reference,physx_buffer_multiplier=16,clear_contact_cache_on_reset=a.clear_planning_cache)
        assert .6<=a.hand_motor_span<=1.5
        e.span[7:]=a.hand_motor_span
        e.steps=int(round(a.seconds*30));dev=e.device
        mean=torch.zeros((4,28),device=dev)
        std=torch.full_like(mean,.16);std[:,27]=.35
        if a.resume:
            old=json.loads((a.resume/'config.json').read_text())
            assert old['source_sha256']==cfg['source_sha256'] and old['reference_sha256']==cfg['reference_sha256']
            mean=torch.as_tensor(np.load(a.resume/'best-training-trace.npz')['knots'],device=dev).clone()
            mean[:,7:27]*=old.get('hand_motor_span_rad',.6)/a.hand_motor_span
            cfg['resume_knots_sha256']=hashlib.sha256((a.resume/'best-training-trace.npz').read_bytes()).hexdigest()
            (a.output/'config.json').write_text(json.dumps(cfg,indent=2))
        std[:,7:27]*=.6/a.hand_motor_span
        best_score=-float('inf');best_knots=mean.clone();best=None
        hand_geometry=HandIntersection()
        start=time.monotonic();log=(a.output/'learning.jsonl').open('w',buffering=1)
        for gen in range(1,a.generations+1):
            if stop[0]:break
            knots=(mean[None]+torch.randn((32,4,28),device=dev)*std[None]).clamp(-1,1)
            knots[0]=best_knots;knots[1]=mean
            # Explicit held-target and delayed-advance seeds exercise true
            # pause while leaving all motors available to the other samples.
            knots[2]=0;knots[2,:,27]=-.75
            knots[3]=0;knots[3,:2,27]=-.75
            knots[4:8]=mean[None]+torch.randn((4,4,28),device=dev)*.25
            knots[4:8,:,7:27]=mean[None,:,7:27]+(knots[4:8,:,7:27]-mean[None,:,7:27])*.6/a.hand_motor_span
            knots.clamp_(-1,1)
            if a.robust:knots[16:]=knots[:16].clone()
            physical_offsets=None
            if a.robust:
                pose_delta=torch.zeros((32,3),device=dev);pose_delta[16:]=torch.tensor([.0003,-.00015,.0001],device=dev)
                joint_delta=torch.zeros((32,27),device=dev);joint_delta[16:]=torch.tensor([.001 if i%2 else -.001 for i in range(27)],device=dev)
                physical_offsets=(pose_delta,joint_delta)
            e.reset(torch.arange(32,device=dev),perturb=False,physical_offsets=physical_offsets)
            held_count=torch.zeros(32,device=dev);lastheld=torch.zeros_like(held_count)
            potential=torch.zeros_like(held_count);finalerror=torch.zeros_like(held_count)
            surface_score=torch.zeros_like(held_count);surface_distance=torch.zeros_like(held_count)
            near_limit_cost=torch.zeros_like(held_count)
            target_history=[];q_history=[];object_history=[];phase_history=[]
            for tick in range(e.steps):
                t=tick/(e.steps-1)*3;i=min(2,int(t));f=t-i
                action=knots[:,i]*(1-f)+knots[:,i+1]*f
                _,_,_,info=e.step(action)
                margin=torch.minimum(e.dof[:,7:27,0]-e.limitlow[7:27],e.limithi[7:27]-e.dof[:,7:27,0]).amin(-1)
                near_limit_cost+=(.015-margin).clamp(0,.015)/.015
                held_count+=info['held'].float()
                if tick>=e.steps-30:
                    lastheld+=info['held'].float()
                    potential+=info['potential'];finalerror+=info['error']
                    count=len(e.thumb_vertices);pad=e.rb[:,e.pad_indices[0]];slider=e.rb[:,e.slider_index]
                    vertices=quat_apply(pad[:,None,3:7].expand(-1,count,-1).reshape(-1,4),e.thumb_vertices[None].expand(32,-1,-1).reshape(-1,3)).reshape(32,count,3)+pad[:,None,:3]
                    inv=quat_conjugate(slider[:,3:7])
                    local=quat_apply(inv[:,None].expand(-1,count,-1).reshape(-1,4),(vertices-slider[:,None,:3]).reshape(-1,3)).reshape(32,count,3)
                    distance=(local.abs()-e.slider_half[:,None]).clamp_min(0).norm(dim=-1).amin(-1)
                    surface_distance+=distance
                    surface_score+=torch.exp(-distance/.01)*info['held'].float()
                target_history.append(e.command_target.clone())
                q_history.append(e.dof[:,:27,0].clone())
                object_history.append(e.rb[:,e.object_index].clone());phase_history.append(e.phase.clone())
            # A dropped knife cannot beat a sustained carried candidate.
            score=100*potential/30+5*held_count/e.steps-100*(30-lastheld)/30
            if a.functional_intake:
                score=30*potential/30+70*surface_score/30+5*held_count/e.steps-100*(30-lastheld)/30
            score-=30*near_limit_cost/e.steps
            rank=torch.minimum(score[:16],score[16:]) if a.robust else score
            q_cpu=None
            rejected_geometry=0
            for attempt in range(4):
                candidate=int(rank.argmax())
                ix=candidate+16 if a.robust and score[candidate+16]<score[candidate] else candidate
                value=float(rank[candidate]);improved=value>best_score+1e-5
                if not improved:break
                if q_cpu is None:q_cpu=torch.stack(q_history).cpu().numpy()
                members=[candidate,candidate+16] if a.robust else [candidate]
                invalid=any(hand_geometry.inspect(q[7:]) for member in members for q in q_cpu[:,member])
                if not invalid:break
                rank[candidate]=-1000;rejected_geometry+=1;improved=False
            if improved:
                best_score=value;best_knots=knots[ix].clone()
                best=dict(generation=gen,score=value,final_held_frames=int(lastheld[ix]),
                          final_entry_error=float(finalerror[ix]/30),
                          held_seconds=float(held_count[ix]/30),phase=float(e.phase[ix]),
                          paired_worst_outcome=a.robust,
                          final_thumb_surface_gap_m=float(surface_distance[ix]/30),
                          near_joint_limit_cost=float(near_limit_cost[ix]/e.steps),
                          scope='Fitted native course; original B and independent episode untested')
                motor=torch.stack(target_history)[:,ix].cpu().numpy()
                np.savez_compressed(a.output/'best-training-trace.npz',targets=motor,
                    q=torch.stack(q_history)[:,ix].cpu().numpy(),
                    object=torch.stack(object_history)[:,ix].cpu().numpy(),
                    phase=torch.stack(phase_history)[:,ix].cpu().numpy(),
                    knots=best_knots.cpu().numpy())
                recipe={'required_actual_source':a.source,'development_abort_on_translation_m':.08,
                        'rows':[dict(time_s=(i+1)/30,arm_q=r[:7].tolist(),hand_q=r[7:].tolist()) for i,r in enumerate(motor)],
                        'optimization':best,'scope':cfg['scope']}
                issued=np.load(Path(a.source,'takeover.npz'))['issued_target']
                recipe['rows'].insert(0,dict(time_s=0,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist()))
                (a.output/'best-motor.json').write_text(json.dumps(recipe,indent=2))
                (a.output/'best-result.json').write_text(json.dumps(best,indent=2))
                snapshot=a.output/'frozen'/('generation_%03d'%gen)
                snapshot.mkdir(parents=True,exist_ok=False)
                for name in ['best-training-trace.npz','best-motor.json','best-result.json']:
                    (snapshot/name).write_bytes((a.output/name).read_bytes())
            elite=knots[rank.topk(4).indices]
            mean=.25*mean+.75*elite.mean(0)
            std=.25*std+.75*elite.std(0,unbiased=False)
            std[:,:27].clamp_(min=.025,max=.35);std[:,27].clamp_(min=.08,max=.6)
            row=dict(generation=gen,elapsed_s=time.monotonic()-start,batch_best=value,
                     best=best,terminal_held_candidates=int((lastheld==30).sum()),
                     motor_std=float(std[:,:27].mean()),phase_std=float(std[:,27].mean()),
                     rejected_geometry_candidates=rejected_geometry,
                     phase_completion_certifies_nothing=True)
            log.write(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
            if improved:
                record('correlated_course_training_candidate_improved',[str(a.output/'best-result.json'),str(a.output/'best-motor.json')],best,
                       next_step='Independent native replay and complete original B takeover required')
            if best is not None and best['final_held_frames']==30 and (best['final_thumb_surface_gap_m']<.001 if a.functional_intake else best['final_entry_error']<.65):break
        log.close()
    finally:
        if e is not None:e.close()
        record('correlated_full_motor_course_terminal',[str(a.output)],updates={'remove_active_jobs':[str(a.output)]},
               next_step='Replay best physically; training trace is not acceptance')


if __name__=='__main__':main()
