"""Original and multiasset baseline parity; fixed fresh states, separate processes."""
import argparse
import copy
import json
import random
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch
from scripts.wuji_student_interface import load_artifact, tensor_hash, legal_policy_observation
from isaacgymenvs.utils.distill_rollout_utils import distillation_action
from scripts.wuji_width_contract import ROUND, sha, slots
from scripts.record_wuji_width_goal import R,D,record


def fixture(output):
    manifest=json.loads((D/'data/C-training.json').read_text())
    pools={p['source']:p for p in manifest['pools'] if p['group']==0}
    arrays={s:np.load(R/p['states'],allow_pickle=False) for s,p in pools.items()}
    for s,p in pools.items():assert sha(R/p['states'])==p['sha256']
    used={s:0 for s in arrays};rows=[]
    for slot in slots('C'):
        source=slot['source'];row=used[source];assert row<len(arrays[source])
        rows.append(arrays[source][row]);used[source]+=1
    output.mkdir(parents=True,exist_ok=False)
    np.save(output/'states.npy',np.stack(rows))
    (output/'manifest.json').write_text(json.dumps(dict(states_sha256=sha(output/'states.npy'),
        source_slots=slots('C'),n=256,source_counts=used,source_kind='fresh statically accepted baseline training pool',
        historical_final_access=False),indent=2)+'\n')
    record('zero_change_fixture_registered',evidence=str(output/'manifest.json'),
           next='Run original and multiassetC in separate finite processes on one backend; numerical comparison only')


def capture(a):
    fixture_path=R/a.fixture
    states=np.load(fixture_path/'states.npy',allow_pickle=False)
    assert sha(fixture_path/'states.npy')==json.loads((fixture_path/'manifest.json').read_text())['states_sha256']
    assert states.shape==(256,75)
    if a.backend=='H200':assert 'H200' in torch.cuda.get_device_name(0)
    a.output.mkdir(parents=True,exist_ok=False)
    overrides=['hand=wuji_paper_official_actuator','task.env.episodeLength=600',
               'task.env.proprioHistoryLen=50','task.env.studentInitObsDim=55','+task.env.enableStudentEncoderObs=True']
    if a.path=='original':
        task='wuji_multigrasp';overrides+=['object=knife_wuji_bridge3_20260922',
                'task.env.trainingStates='+str((fixture_path/'states.npy').relative_to(R))]
    else:
        task='wuji_width_student';overrides+=['object=knife_wuji_width_train_20261002','task.env.widthArm=C',
                'task.env.widthTrainingManifest=research/'+ROUND+'/data/C-training.json']
    cfg=configuration(task,256,overrides,train='wujiAcquisitionSAPG',seed=2026100215)
    teacher=R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth'
    student=R/'runs/unified-student-20261001/SA-real-51200/step_051200.pth'
    env,player=make_player(cfg,teacher)
    try:
        fixed=torch.as_tensor(states,device=env.device)
        env.sample_grasps=lambda ids:fixed[ids]
        artifact=load_artifact(player,env,student)
        player.model.eval()
        for param in player.model.parameters():param.requires_grad_(False)
        before=tensor_hash(player.model.state_dict())
        # Shared reset RNG after model/env construction isolates slot-selection
        # machinery from any differing constructor RNG consumption.
        torch.manual_seed(2026100217);torch.cuda.manual_seed_all(2026100217)
        np.random.seed(2026100217);random.seed(2026100217)
        obs=player.env_reset(player.env);frames=[];replay_differences=[]
        for step in range(8):
            x=env.student_obs_buf.detach().clone();public=legal_policy_observation(obs)
            incoming=[s.clone() for s in player.states]
            with torch.no_grad():
                action=distillation_action(player,obs,x,None,False,True,True)
                after=[s.clone() for s in player.states]
            # Independent second forward with the identical legal public input,
            # temporal/controller input and incomingRNN; live state restored.
            player.states=[s.clone() for s in incoming]
            with torch.no_grad():replay=distillation_action(player,obs,x,None,False,True,True)
            delta=float((action-replay).abs().max());assert delta<2e-5
            assert all(torch.equal(s,t) for s,t in zip(after,player.states))
            player.states=after;replay_differences.append(delta)
            frames.append(dict(public=public.cpu().numpy(),x=x.cpu().numpy(),action=action.cpu().numpy(),
                target=env.actions_to_targets(action).detach().cpu().numpy(),rnn=np.stack([s.cpu().numpy() for s in after]),
                incoming=np.stack([s.cpu().numpy() for s in incoming])))
            obs,_,done,_=player.env_step(player.env,action)
            assert not done.any(), 'Short parity fixture reset; do not silently re-pair states'
        assert before==tensor_hash(player.model.state_dict())
        np.savez_compressed(a.output/'trace.npz',**{k:np.stack([f[k] for f in frames]) for k in frames[0]})
        report=dict(path=a.path,backend=a.backend,device=torch.cuda.get_device_name(0),steps=8,envs=256,
            fixture_sha256=sha(fixture_path/'states.npy'),teacher_sha256=sha(teacher),student_sha256=sha(student),
            model_unchanged=True,full_model_hash=before,max_same_input_replay_action_error=max(replay_differences),
            original_training_pool_used=False,optimizer_updates=0,scope='Zero geometry change infrastructure check; short fixed reset states, no capability/final evidence')
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:env.gym.destroy_sim(env.sim)


def compare(a):
    left=json.loads((a.original/'report.json').read_text());right=json.loads((a.multiasset/'report.json').read_text())
    for key in ['backend','device','fixture_sha256','teacher_sha256','student_sha256','full_model_hash']:
        assert left[key]==right[key],key
    with np.load(a.original/'trace.npz') as x,np.load(a.multiasset/'trace.npz') as y:
        differences={key:float(np.max(abs(x[key]-y[key]))) for key in x.files}
    limits=dict(public=2e-6,x=2e-6,action=2e-5,target=2e-6,rnn=2e-4,incoming=2e-4)
    passed=all(differences[k]<=v for k,v in limits.items())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(passed=passed,backend=left['backend'],device=left['device'],differences=differences,tolerances=limits,
        original=str(a.original),multiasset=str(a.multiasset),fixture_sha256=left['fixture_sha256'],
        scope='Original vs zero-change multiassetC path on same device; no H200 certification from local preparation')
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    record('zero_change_path_comparison_passed' if passed else 'zero_change_path_comparison_failed',evidence=str(a.output),
           next='H200 inventory/remaining prechecks when connection is usable' if passed else 'Inspect concrete parity differences; do not tune tolerances or begin formal training')
    print(json.dumps(report));assert passed


def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    f=s.add_parser('fixture');f.add_argument('--output',type=Path,required=True)
    c=s.add_parser('capture');c.add_argument('--path',choices=['original','multiasset'],required=True)
    c.add_argument('--backend',choices=['local-preparation','H200'],required=True);c.add_argument('--fixture',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    v=s.add_parser('compare');v.add_argument('--original',type=Path,required=True);v.add_argument('--multiasset',type=Path,required=True);v.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    fixture(a.output) if a.mode=='fixture' else capture(a) if a.mode=='capture' else compare(a)


if __name__=='__main__':main()
