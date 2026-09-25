"""Check which knife body each fingertip contacts after a fresh candidate reset.

CPU tensor pipeline permits explicit PhysX rigid-contact queries. It is a
separate two-second contact check, not a bitwise repeat of the GPU-pipeline
20-second stability test. Report every candidate and all original source rows.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
from scripts.filter_wuji_fingertip_grasps import RULES
from isaacgym import gymapi
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--object',default='knife_wuji_fingertip_precision000')
    args=parser.parse_args()
    source=Path(__file__).read_bytes()
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'report.json').exists()
    states=np.load(args.candidates/'initial_states.npy')
    manifest=json.loads((args.candidates/'manifest.json').read_text())
    assert hashlib.sha256((args.candidates/'initial_states.npy').read_bytes()).hexdigest()==manifest['states_sha256']
    cfg=configuration('wuji_acquisition_official_support40mrad',len(states),
        ['object='+args.object,'hand=wuji_paper_official_actuator',
         'test=True','pipeline=cpu','task.env.episodeLength=600'],train='wujiAcquisitionSAPG',seed=20261017)
    assert cfg.object.asset.asset_root==manifest['expected_object_asset_root']
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    (args.output/'source.py').write_bytes(source)
    env=make_env(cfg)
    frames=[]
    try:
        assert not env.gym.get_sim_params(env.sim).use_gpu_pipeline
        env.configure_fixed_grasp_consecutive_evaluation('000',states[0],
            goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=len(states))
        env.eval_grasp_states[:]=torch.as_tensor(states,device=env.device)
        env.success_hold_duration=1e9;env.eval_goal_timeout=0.
        hand=env.gym.find_actor_handle(env.envs[0],'hand')
        pads=env.force_handles.cpu().tolist()
        palm=env.gym.find_actor_rigid_body_index(env.envs[0],hand,'hand_r_base_link',gymapi.DOMAIN_ENV)
        bodies=[int(env.object_rb_handles[0]),int(env.object_rb_handles[1])]
        assert len(pads)==5 and 'thumb' in cfg.hand.force_links[0]
        original=env.compute_reward
        step=[0]

        def capture(actions):
            active=env.eval_active_mask.detach().cpu().numpy().copy()
            original(actions);step[0]+=1
            if step[0]%3:return
            contact=np.zeros((len(states),5),dtype=bool)
            palm_touch=np.zeros(len(states),dtype=bool)
            counts=np.zeros(len(states),dtype=np.int32)
            for i,handle in enumerate(env.envs):
                for c in env.gym.get_env_rigid_contacts(handle):
                    if float(c['lambda'])<=RULES['contact_force_threshold']:continue
                    counts[i]+=1
                    pair={int(c['body0']),int(c['body1'])}
                    palm_touch[i]|=palm in pair and bool(pair & set(bodies))
                    for finger,pad in enumerate(pads):
                        target=bodies[1] if finger==0 else bodies[0]
                        contact[i,finger]|=pair=={int(pad),target}
            frames.append(dict(active=active,contact=contact,palm=palm_touch,contact_count=counts,
                               fall=env.debug_reset_cause_fall.cpu().numpy().copy(),
                               invalid=env.debug_reset_cause_invalid.cpu().numpy().copy()))

        env.compute_reward=capture;env.reset()
        for _ in range(60):env.step(torch.zeros((len(states),20),device=env.device))
        trace={k:np.stack([f[k] for f in frames]) for k in frames[0]}
        assert trace['contact'].shape==(20,len(states),5)
        assert trace['contact_count'].sum()>0,'No rigid contacts returned; cannot interpret absent contacts as failures'
        np.savez_compressed(args.output/'trace.npz',**trace)
        rows=[]
        for i in range(len(states)):
            valid=trace['active'][:,i]&~trace['fall'][:,i]&~trace['invalid'][:,i]
            fractions=(trace['contact'][:,i]&valid[:,None]).mean(axis=0)
            palm_fraction=float(trace['palm'][:,i].mean())
            rows.append(dict(candidate_row=i,survived2s=bool(valid.all()),
                correct_body_contact_fraction=fractions.tolist(),palm_contact_fraction=palm_fraction,
                passed_existing_contact_rule=bool(valid.all() and (fractions>=.9).all() and palm_fraction==0.),
                thumb_and_two_supports=bool(valid.all() and fractions[0]>=.9 and (fractions[1:]>=.9).sum()>=2 and palm_fraction==0.)))
        result=dict(status='completed',scope=__doc__,records=rows,num_candidates=len(states),
                    source_counts=manifest['source_counts'],rules=RULES,
                    all_five_contact_passes=sum(r['passed_existing_contact_rule'] for r in rows),
                    thumb_two_support_passes=sum(r['thumb_and_two_supports'] for r in rows),
                    initial_states_sha256=manifest['states_sha256'],source_sha256=hashlib.sha256(source).hexdigest(),
                    finger_order=list(cfg.hand.force_links),
                    note='The thumb-plus-two-support statistic is diagnostic only; it does not replace the existing five-finger contact filter.')
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ['records','rules','scope']}),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
