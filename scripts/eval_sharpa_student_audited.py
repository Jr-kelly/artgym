"""Original consecutive evaluator with explicit student-control checks."""
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import torch
from scripts.audit_distillation_runtime import tensor_digest


def main():
    from isaacgymenvs import infer_student_impl,eval_consecutive
    original=infer_student_impl.build_student_encoder_from_artifact
    artifact=Path(sys.argv[sys.argv.index('--student-artifact')+1])
    checkpoint=Path(sys.argv[sys.argv.index('--checkpoint')+1])
    payload=torch.load(artifact,map_location='cpu')
    assert payload['distill_meta']['hand']=='sharpa'
    assert payload['distill_meta']['teacher_checkpoint_sha256']==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    checks=dict(actual_actions=0,restricted_inputs=0,privileged_invariance=0)
    refs={}
    def build(*args,**kwargs):
        result=original(*args,**kwargs);encoder=result[0];player=kwargs['player'];env=player.env.env
        assert tensor_digest(encoder.state_dict())==tensor_digest(payload['student_encoder_state_dict'])
        refs.update(encoder=encoder,player=player,initial_encoder=tensor_digest(encoder.state_dict()))
        old_action=player.get_action;pre=env.pre_physics_step;expected=[]
        def before(action):
            pre(action)
            assert torch.equal(env.actions,expected[0])
            checks['actual_actions']+=env.num_envs
        env.pre_physics_step=before
        def act(obs,*args,**kwargs):
            model=player.model
            assert model.a2c_network.priv_encoder is encoder and not encoder.training
            history=model.a2c_network.actor_encoder_obs_override
            assert history.shape==(env.num_envs,2257)
            assert torch.equal(history,env.get_student_encoder_observations())
            if 'model_before' not in refs:refs['model_before']=tensor_digest(model.state_dict())
            incoming=[v.clone() for v in player.states]
            action=old_action(obs,*args,**kwargs);outgoing=[v.clone() for v in player.states]
            if checks['actual_actions']<3*env.num_envs:
                with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
                    changed=obs.clone();changed[:,117:143]=123.
                    player.states=[v.clone() for v in incoming]
                    counterfactual=old_action(changed,*args,**kwargs)
                    assert torch.equal(counterfactual,action)
                    assert all(torch.equal(a,b) for a,b in zip(player.states[:2],outgoing[:2]))
                    player.states=outgoing
                checks['privileged_invariance']+=env.num_envs
            checks['restricted_inputs']+=env.num_envs
            expected[:]=[action.clone()]
            return action
        player.get_action=act
        return result
    infer_student_impl.build_student_encoder_from_artifact=build
    try:eval_consecutive.main()
    finally:infer_student_impl.build_student_encoder_from_artifact=original
    assert checks['actual_actions']==checks['restricted_inputs']>0
    assert checks['privileged_invariance']>0
    assert tensor_digest(refs['encoder'].state_dict())==refs['initial_encoder']
    assert tensor_digest(refs['player'].model.state_dict())==refs['model_before']
    out=Path(sys.argv[sys.argv.index('--summary-output')+1]);d=json.loads(out.read_text())
    d['student_audit']=dict(status='passed',checks=checks,weights_unchanged=True,
        teacher_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        student_artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        encoder_tensor_sha256=refs['initial_encoder'],completed_updates=payload['distill_meta']['completed_updates'],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Student alone drives physics using50x44+57history/initialinputs, original frozenactor. Original10mm consecutivecycles, 10repeats, heldoutgeometry; not2mmWuJifixedclock, finalpaperreproduction orhardware.')
    out.write_text(json.dumps(d,indent=2)+'\n')
    out.with_suffix('.audit-source.py').write_bytes(Path(__file__).read_bytes())


if __name__=='__main__':main()
