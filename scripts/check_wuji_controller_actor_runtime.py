"""Gate controller residual inputs against the unchanged CP25 actor in physics."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
import torch
from omegaconf import OmegaConf
from scripts.train_wuji_student_actor import register
from scripts.check_wuji_student_actor_runtime import overrides, STUDENT_SHA
from scripts.audit_distillation_runtime import tensor_digest
from isaacgymenvs.learning.wuji_fixed_student_actor import WujiFixedStudentBuilder
from isaacgymenvs.distill import reset_done_rnn_states


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--enabled', choices=['true','false'], required=True)
    parser.add_argument('--steps', type=int, default=600)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'report.json').exists()
    register()
    requested = overrides()+['train.params.network.controller_adapter.enabled='+args.enabled,
                             'task.env.absolutePoseObjective.ramp_epochs=0']
    cfg = configuration('wuji_controller_student_actor', 32, requested,
                        train='wujiControllerStudentSAPG', seed=20261065)
    (output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env, player = make_player(cfg,args.checkpoint)
    player.model.eval()
    assert player.model.a2c_network.controller_enabled == (args.enabled == 'true')
    reference = copy.deepcopy(player.model)
    reference.a2c_network.__class__ = WujiFixedStudentBuilder.Network
    ref_player = copy.copy(player)
    ref_player.model = reference
    ref_player.obs_shape = (154,)
    before = tensor_digest(player.model.state_dict())
    encoder_before = tensor_digest(env.fixed_student_encoder.state_dict())
    checks = dict(transitions=0, matched_actions=0, current_input_matches=0,
                  actor_privileged_invariance=0, paired_mode_invariance=0,
                  sampled_rows=[0,0,0], nonzero_tracking_entries=0)
    devices = [torch.device(player.device).index or 0]
    physical = hashlib.sha256()
    observation = player.env_reset(player.env)
    network = player.model.a2c_network
    try:
        for step in range(args.steps):
            expected = ((env.cur_targets[:,:20]-env.hand_dof_pos)/.1).clamp(-5.,5.)
            assert torch.equal(observation[:,153:173], expected)
            checks['current_input_matches'] += env.num_envs
            checks['nonzero_tracking_entries'] += int(expected.count_nonzero())
            incoming = [x.clone() for x in player.states]
            with torch.no_grad():
                action = player.get_action(observation, is_deterministic=True)
                outgoing = [x.clone() for x in player.states]
                with torch.random.fork_rng(devices=devices):
                    ref_player.states = [x.clone() for x in incoming]
                    old_obs = torch.cat([observation[:,:153],observation[:,173:174]],dim=1)
                    old_action = ref_player.get_action(old_obs,is_deterministic=True)
                    assert torch.equal(action, old_action)
                    assert all(torch.equal(a,b) for a,b in zip(outgoing,ref_player.states))
                    checks['matched_actions'] += env.num_envs
                    # Compare both modes at exactly the same physical state,
                    # same observation and incoming RNN; discard the extra call.
                    original_enabled = network.controller_enabled
                    try:
                        network.controller_enabled = not original_enabled
                        player.states = [x.clone() for x in incoming]
                        paired_action = player.get_action(observation,is_deterministic=True)
                        assert torch.equal(action,paired_action)
                        assert all(torch.equal(a,b) for a,b in zip(outgoing,player.states))
                        checks['paired_mode_invariance'] += env.num_envs
                    finally:
                        network.controller_enabled = original_enabled
                    wrong = observation.clone()
                    wrong[:,111:137] = torch.randn_like(wrong[:,111:137])*10+25
                    player.states = [x.clone() for x in incoming]
                    wrong_action = player.get_action(wrong,is_deterministic=True)
                    assert torch.equal(action,wrong_action)
                    assert all(torch.equal(a,b) for a,b in zip(outgoing[:2],player.states[:2]))
                    checks['actor_privileged_invariance'] += env.num_envs
                player.states = outgoing
            distance=(env.init_hand_dof_pos[:,None,:]-env.all_valid_states[None,:,:20]).abs().amax(-1)
            best,rows=distance.min(-1)
            assert (best<.011).all()
            checks['sampled_rows']=[a+b for a,b in zip(checks['sampled_rows'],torch.bincount(rows,minlength=3).tolist())]
            observation,_,done,_=player.env_step(player.env,action)
            for value in [action,env.hand_dof_pos,env.object_pos,env.object_rot,env.obj_dof_pos,env.cur_targets,done,*player.states[:2]]:
                physical.update(value.detach().cpu().contiguous().numpy().tobytes())
            reset_done_rnn_states(player,done)
            checks['transitions'] += env.num_envs
            if step%100==0:
                print(json.dumps(dict(step=step,checks=checks)),flush=True)
        assert tensor_digest(player.model.state_dict())==before
        assert tensor_digest(env.fixed_student_encoder.state_dict())==encoder_before
        assert min(checks['sampled_rows'])>0 and checks['nonzero_tracking_entries']>0
        # A nonzero adapter must depend on controller features only when enabled.
        # This is a model-only counterfactual after physics, never applied to env.
        original_weight=network.controller_adapter.weight.detach().clone()
        with torch.no_grad(), torch.random.fork_rng(devices=devices):
            network.controller_adapter.weight.copy_(torch.eye(16,20,device=player.device)*.05)
            raw=player.model.norm_obs(observation)
            raw=torch.cat([raw[:,:137],raw[:,173:174],raw[:,137:173]],dim=1)
            changed=raw.clone()
            changed[:,154:174]+=1
            normal=network._fuse_actor_inputs(raw)
            different=network._fuse_actor_inputs(changed)
            assert (not torch.equal(normal,different)) == network.controller_enabled
            privileged=raw.clone()
            privileged[:,111:137]+=123
            assert torch.equal(normal,network._fuse_actor_inputs(privileged))
            assert torch.equal(network._fuse_critic_inputs(raw),network._fuse_critic_inputs(changed))
            network.controller_adapter.weight.copy_(original_weight)
        assert tensor_digest(player.model.state_dict())==before
        player.model.train()
        assert not player.model.running_mean_std.training
        assert not env.fixed_student_encoder.training
        assert all(not x.requires_grad for x in env.fixed_student_encoder.parameters())
        root=Path(__file__).resolve().parents[1]
        files=['scripts/check_wuji_controller_actor_runtime.py','scripts/train_wuji_student_actor.py',
               'scripts/train_wuji_student_actor_audited.py','scripts/wuji_sapg_kl_metrics.py',
               'scripts/prepare_wuji_controller_actor.py','scripts/check_wuji_student_actor_runtime.py',
               'isaacgymenvs/tasks/wuji_controller_student_actor.py','isaacgymenvs/learning/wuji_controller_student_actor.py',
               'isaacgymenvs/tasks/wuji_fixed_student_actor.py','isaacgymenvs/learning/wuji_fixed_student_actor.py',
               'isaacgymenvs/cfg/task/wuji_controller_student_actor.yaml','isaacgymenvs/cfg/train/wujiControllerStudentSAPG.yaml']
        report=dict(status='passed',enabled=network.controller_enabled,checks=checks,
            model_unchanged=True,encoder_unchanged=True,action_and_all_rnn_equal_to_inherited_actor=True,
            same_state_both_modes_actions_and_all_rnn_exact=True,
            nonzero_adapter_features_affect_actor_only_if_enabled=True,nonzero_adapter_actor_privileged_invariance=True,
            critic_independent_of_added_features=True,student_sha256=STUDENT_SHA,
            checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
            physical_action_actor_rnn_sha256=physical.hexdigest(),
            sources={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
            scope='Same-state initial policy equivalence in real rollouts. Independent PhysX processes need not be bitwise identical. No task-success/hardware claim.')
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__=='__main__':
    main()
