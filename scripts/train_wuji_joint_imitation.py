"""Joint temporal-encoder/actor imitation with a frozen privileged teacher.

Teacher owns a separate recurrent history of the same actual student-induced
states. Only the student mean action reaches physics. No privileged label is
inserted into the student observation or recurrent state.
"""
import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch
from torch import nn
from omegaconf import OmegaConf
from rl_games.algos_torch import models
from rl_games.algos_torch.players import rescale_actions
from isaacgymenvs.learning.a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from scripts.train_wuji_student_actor import register
from scripts.check_wuji_student_actor_runtime import overrides, TEACHER, STUDENT_SHA
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now
from isaacgymenvs.distill import reset_done_rnn_states

ROOT = Path(__file__).resolve().parents[1]
INITIAL = ROOT/'runs/wuji-goal/frozen-candidates/student-actorrl-sigmaquarter-broad0-seed62-cp25/actor.pth'
INITIAL_SHA = 'a2d68ba64d0c34fe04fd1ffa408235f0056f2717d779cef70155ef8b37f37b5a'
TEACHER_SHA = '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'


def clone_states(states):
    return [v.detach().clone() for v in states]


@contextmanager
def backward_recurrent(model):
    leaves = [m for m in model.modules() if isinstance(m, nn.RNNBase)]
    assert leaves and all(m.dropout == 0 for m in leaves)
    modes = [m.training for m in leaves]
    try:
        for m in leaves:
            m.training = True  # cuDNN backward reserve, zero dropout only.
        yield
    finally:
        for m, mode in zip(leaves, modes):
            m.training = mode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', choices=['actor', 'joint'], required=True)
    parser.add_argument('--updates', type=int, default=500)
    parser.add_argument('--num-envs', type=int, default=2048)
    parser.add_argument('--lr', type=float, default=1e-5)
    parser.add_argument('--seed', type=int, default=20261068)
    parser.add_argument('--runtime-only', action='store_true')
    args = parser.parse_args()
    assert args.updates > 0 and args.num_envs >= 2 and args.lr >= 0
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    if args.runtime_only:
        assert args.lr == 0 and args.updates == 20 and args.num_envs == 32
    assert hashlib.sha256(INITIAL.read_bytes()).hexdigest() == INITIAL_SHA
    assert hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest() == TEACHER_SHA
    register()
    cfg = configuration('wuji_fixed_student_actor', args.num_envs,
        overrides()+['task.env.absolutePoseObjective.ramp_epochs=0'],
        train='wujiFixedStudentActorSAPG', seed=args.seed)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, INITIAL)
    model = player.model.eval()
    assert not env.eval_mode and env.fixed_student_sha256 == STUDENT_SHA
    assert torch.equal(player.intr_reward_coef_embd[:,0], torch.full((args.num_envs,), 50., device=player.device))
    initial_model = {k:v.detach().clone() for k,v in model.state_dict().items()}
    encoder_before = tensor_digest(env.fixed_student_encoder.state_dict())
    encoder = env.fixed_student_encoder
    for parameter in encoder.parameters():
        parameter.requires_grad_(args.scope == 'joint')
    encoder_initial = {k:v.detach().clone() for k,v in encoder.state_dict().items()}
    # Build the teacher's original138-input network/model without another env.
    teacher_network = copy.deepcopy(model.a2c_network)
    teacher_network.__class__ = A2CSAPGPrivBuilder.Network
    teacher = models.ModelA2CContinuousLogStd.Network(teacher_network, obs_shape=(138,),
        normalize_value=True, normalize_input=True, value_size=1, extra_info_start_idx=137).to(player.device)
    payload = torch.load(ROOT/TEACHER, map_location=player.device)
    payload = payload[0] if 0 in payload else payload
    teacher.load_state_dict(payload['model'])
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    teacher_before = tensor_digest(teacher.state_dict())
    teacher_player = copy.copy(player)
    teacher_player.model = teacher
    teacher_player.obs_shape = (138,)
    teacher_player.states = clone_states(player.states)
    allowed = (
        'a2c_network.actor_mlp.', 'a2c_network.a_rnn.', 'a2c_network.a_layer_norm.',
        'a2c_network.mu.', 'a2c_network.extra_params')
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(name.startswith(allowed))
    parameters = [p for p in model.parameters() if p.requires_grad]
    parameters += [p for p in encoder.parameters() if p.requires_grad]
    assert parameters and not model.training and not model.running_mean_std.training
    optimizer = torch.optim.Adam(parameters, lr=args.lr)
    private = torch.Generator(device=player.device)
    private.manual_seed(args.seed+1000)
    devices = [torch.device(player.device).index or 0]
    checks = dict(student_only_physics_transitions=0, teacher_label_transitions=0,
        current_privileged_invariance_checks=0, driver_action_parity=0, recurrent_resets=0,
        replay_max_mean_error=0., replay_max_rnn_error=0., teacher_driver_parity=0,
        pre_physics_action_checks=0, reset_action_buffer_checks=0,
        encoder_replay_max_error=0., encoder_input_layout_checks=0)
    # ArtManip clears actions during post_physics_step/reset_idx. Capture the
    # actual control input after its conversion and before gym.simulate instead.
    original_pre_physics_step = env.pre_physics_step
    applied_actions = []
    def capture_pre_physics_step(actions):
        original_pre_physics_step(actions)
        applied_actions.append(env.actions.detach().clone())
    env.pre_physics_step = capture_pre_physics_step
    physics_hash = hashlib.sha256()
    state = dict(status='running', started=now(), scope=args.scope, updates_completed=0,
        initial_sha256=INITIAL_SHA, teacher_sha256=TEACHER_SHA, student_sha256=STUDENT_SHA,
        arguments=vars(args).copy(), trainable_names=[n for n,p in model.named_parameters() if p.requires_grad])
    state['arguments']['output'] = str(args.output)
    atomic_json(args.output/'status.json', state)
    observations = player.env_reset(player.env)
    previous_done = torch.zeros(args.num_envs, dtype=torch.float32, device=player.device)
    records = []
    first_initial = torch.cat([env.hand_dof_pos, env.object_pos, env.object_rot, env.obj_dof_pos], -1)
    np.save(args.output/'initial-state.npy', first_initial.detach().cpu().numpy())
    first_initial_sha = hashlib.sha256((args.output/'initial-state.npy').read_bytes()).hexdigest()

    def save(update):
        path = args.output/'checkpoints'/('epoch_%06d.pth'%update)
        path.parent.mkdir(exist_ok=True)
        assert not path.exists()
        temporary = path.with_suffix('.tmp')
        checkpoint = dict(model={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
            joint_encoder_state_dict={k:v.detach().cpu().clone() for k,v in encoder.state_dict().items()},
            epoch=update, frame=update*32*args.num_envs,
            imitation=dict(scope=args.scope, teacher_sha256=TEACHER_SHA, initial_student_sha256=STUDENT_SHA,
                initial_sha256=INITIAL_SHA, loss='raw20GaussianmeanMSE', teacher_memory='own recurrent history of student-induced physical states',
                rollout='student deterministic means only', optimizer='newAdam', learning_rate=args.lr,
                encoder_trainable=args.scope=='joint', encoder_dropout='disabled in rollout and optimization',
                recurrent_boundary='detached hidden state produced by previous weights; encoder refreshed after each optimizer batch'),
            optimizer=optimizer.state_dict())
        torch.save(checkpoint, temporary)
        os.replace(temporary, path)
        atomic_json(path.with_suffix('.json'), dict(epoch=update, frame=checkpoint['frame'],
            checkpoint=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), committed=now()))

    try:
        save(0)
        for update in range(1, args.updates+1):
            # env_step returned a latent computed before the preceding update.
            # Refresh only this deterministic feature; no physics/history/RNN step.
            with torch.no_grad():
                observations[:,137:153] = encoder(env.get_student_encoder_observations())
            incoming = clone_states(player.states)
            raw, histories, means, labels, masks = [], [], [], [], []
            for t in range(32):
                assert observations.shape == (args.num_envs,154)
                assert (observations[:,-1] == 50).all()
                history = env.get_student_encoder_observations().detach().clone()
                assert history.shape == (args.num_envs,2055)
                if args.runtime_only:
                    expected = torch.cat([env.proprioception_buf.reshape(args.num_envs,-1),env._get_init_obs()],-1)
                    assert torch.equal(history,expected)
                    checks['encoder_input_layout_checks'] += args.num_envs
                pre_states = clone_states(player.states)
                # Use the exact existing player path for the real action.
                captured = {}
                def capture_result(module, inputs, result):
                    captured['mu'] = result['mus'].detach().clone()
                handle = model.register_forward_hook(capture_result)
                try:
                    action = player.get_action(observations, is_deterministic=True)
                finally:
                    handle.remove()
                mean = captured['mu']
                post_states = clone_states(player.states)
                assert torch.equal(action, rescale_actions(player.actions_low,player.actions_high,mean.clamp(-1,1)))
                checks['driver_action_parity'] += args.num_envs
                legacy = torch.cat([observations[:,:137], observations[:,153:154]], dim=1)
                with torch.no_grad(), torch.random.fork_rng(devices=devices):
                    result = teacher(dict(is_train=False, prev_actions=None,
                        obs=teacher_player._preproc_obs(legacy), rnn_states=teacher_player.states))
                    label = result['mus'].detach().clone()
                    if args.runtime_only:
                        reference_in = clone_states(teacher_player.states)
                        reference_action = teacher_player.get_action(legacy, is_deterministic=True)
                        assert torch.equal(reference_action,rescale_actions(teacher_player.actions_low,teacher_player.actions_high,label.clamp(-1,1)))
                        assert all(torch.equal(a,b) for a,b in zip(teacher_player.states,result['rnn_states']))
                        teacher_player.states = reference_in
                        checks['teacher_driver_parity'] += args.num_envs
                        changed = observations.clone()
                        changed[:,111:137] = 123+torch.randn_like(changed[:,111:137])
                        player.states = clone_states(pre_states)
                        wrong_action = player.get_action(changed,is_deterministic=True)
                        assert torch.equal(action,wrong_action)
                        assert all(torch.equal(a,b) for a,b in zip(player.states[:2],post_states[:2]))
                        checks['current_privileged_invariance_checks'] += args.num_envs
                    teacher_player.states = clone_states(result['rnn_states'])
                    player.states = post_states
                raw.append(observations.detach().clone())
                histories.append(history)
                means.append(mean)
                labels.append(label)
                masks.append(previous_done.clone())
                applied_actions.clear()
                observations, _, done, _ = player.env_step(player.env, action)
                checks['student_only_physics_transitions'] += args.num_envs
                checks['teacher_label_transitions'] += args.num_envs
                assert len(applied_actions) == 1
                assert torch.equal(applied_actions[0], action), 'pre_physics_action'
                checks['pre_physics_action_checks'] += args.num_envs
                previous_done = done.to(player.device,dtype=torch.float32)
                expected_buffer = action.clone()
                expected_buffer[previous_done.bool()] = 0
                assert torch.equal(env.actions, expected_buffer), 'post_reset_action_buffer'
                checks['reset_action_buffer_checks'] += int(done.sum())
                reset_done_rnn_states(player, done)
                reset_done_rnn_states(teacher_player, done)
                checks['recurrent_resets'] += int(done.sum())
                if args.runtime_only:
                    for value in [action,env.hand_dof_pos,env.object_pos,env.object_rot,env.obj_dof_pos,*player.states[:2]]:
                        physics_hash.update(value.detach().cpu().contiguous().numpy().tobytes())
            raw = torch.stack(raw,dim=1)  # env, time, feature; same order as recurrent builder.
            histories = torch.stack(histories,dim=1)
            targets = torch.stack(labels,dim=1)
            rollout_means = torch.stack(means,dim=1)
            masks = torch.stack(masks,dim=1)
            live_before = clone_states(player.states)
            teacher_live_before = clone_states(teacher_player.states)

            def forward(ids, check_encoder=False):
                states=[s[:,ids,:].detach().clone() for s in incoming]
                outputs=[]
                for index in range(32):
                    keep=(1.-masks[ids,index]).reshape(1,-1,1)
                    states=[s*keep for s in states]
                    latent = encoder(histories[ids,index])
                    if check_encoder:
                        difference=float((latent-raw[ids,index,137:153]).abs().max())
                        checks['encoder_replay_max_error']=max(checks['encoder_replay_max_error'],difference)
                        assert difference<5e-5,('encoder_replay',update,index,difference)
                    # norm_obs intentionally disables autograd. Normalize the
                    # old prefix first, then insert the unnormalized latent
                    # so the action loss reaches the temporal encoder.
                    normalized = model.norm_obs(raw[ids,index])
                    inputs = torch.cat([normalized[:,:137],latent,normalized[:,153:]],-1)
                    result=model.a2c_network(dict(obs=inputs,
                        rnn_states=states,seq_length=1))
                    outputs.append(result[0])
                    states=result[3]
                # Keep the graph across all32 steps, while using the same
                # one-step recurrent arithmetic as deployed policy inference.
                return torch.stack(outputs,dim=1).reshape(-1,20),None,None,states

            # Sequence replay is checked before the first optimizer step in
            # every real batch. PhysX is never stepped by these computations.
            subset=torch.arange(args.num_envs,device=player.device)
            with torch.no_grad(), backward_recurrent(model):
                replay=forward(subset,check_encoder=True)
                error=float((replay[0].reshape(len(subset),32,20)-rollout_means[subset]).abs().max())
                checks['replay_max_mean_error']=max(checks['replay_max_mean_error'],error)
                assert error<5e-5, ('sequence_replay_mean',update,error)
                expected_states=clone_states(player.states)
                # Last post-action done reset is outside network replay.
                for value in replay[3]:
                    value[:,previous_done[subset].bool(),:]=0
                rnn_error=max(float((a-b[:,subset,:]).abs().max()) for a,b in zip(replay[3],expected_states))
                checks['replay_max_rnn_error']=max(checks['replay_max_rnn_error'],rnn_error)
                assert rnn_error<5e-5, ('sequence_replay_rnn',update,rnn_error)
            order=torch.randperm(args.num_envs,device=player.device,generator=private)
            loss_sum=grad_max=0.
            for ids in order.split(min(args.num_envs,512)):
                optimizer.zero_grad(set_to_none=True)
                with backward_recurrent(model):
                    predicted=forward(ids)[0].reshape(len(ids),32,20)
                    loss=(predicted-targets[ids]).square().mean()
                    assert torch.isfinite(loss)
                    loss.backward()
                if args.scope=='joint':
                    gradients=[p.grad for p in encoder.parameters() if p.requires_grad]
                    assert gradients and all(g is not None and torch.isfinite(g).all() for g in gradients)
                    assert sum(float(g.abs().sum()) for g in gradients)>0, 'encoder_gradient_missing'
                gradient=torch.nn.utils.clip_grad_norm_(parameters,1.)
                assert torch.isfinite(gradient) and float(gradient)>0
                grad_max=max(grad_max,float(gradient))
                optimizer.step()
                loss_sum+=float(loss)*len(ids)
            assert all(torch.equal(a,b) for a,b in zip(player.states,live_before))
            assert all(torch.equal(a,b) for a,b in zip(teacher_player.states,teacher_live_before))
            assert not model.running_mean_std.training and not env.fixed_student_encoder.training
            assert all(torch.isfinite(p).all() for p in parameters)
            row=dict(update=update, mean_action_mse=float((rollout_means-targets).square().mean()),
                supervised_loss=loss_sum/args.num_envs, maximum_gradient_norm=grad_max,
                replay_mean_error=error, recurrent_error=rnn_error,
                physics_transitions=checks['student_only_physics_transitions'])
            records.append(row)
            with (args.output/'metrics.jsonl').open('a') as f:
                f.write(json.dumps(row)+'\n')
            print(json.dumps(row),flush=True)
            if update==1 or update%25==0 or update==args.updates:
                save(update)
            state.update(updates_completed=update, heartbeat=now(),checks=checks)
            atomic_json(args.output/'status.json',state)
        changed=[]
        for name,before in initial_model.items():
            after=model.state_dict()[name]
            assert torch.isfinite(after).all()
            if not torch.equal(before,after):
                changed.append(name)
                assert name.startswith(allowed),name
        assert tensor_digest(teacher.state_dict())==teacher_before
        encoder_changed=[n for n,v in encoder.state_dict().items() if not torch.equal(v,encoder_initial[n])]
        if args.lr>0 and args.scope=='joint':
            assert encoder_changed
            assert any(n.startswith('temporal_model.') for n in encoder_changed)
            assert any(n.startswith('latent_head.') for n in encoder_changed)
        else:
            assert tensor_digest(encoder.state_dict())==encoder_before and not encoder_changed
        if args.lr>0:
            assert any(n.startswith('a2c_network.mu.') for n in changed)
            if args.scope in ('actor','joint'):
                assert any(n.startswith('a2c_network.a_rnn.') for n in changed)
                assert any(n.startswith('a2c_network.actor_mlp.') for n in changed)
        else:
            assert not changed
        if args.runtime_only:
            assert checks['recurrent_resets']>=args.num_envs
            assert checks['teacher_driver_parity']==checks['student_only_physics_transitions']==20480
        report=dict(status='passed',finished=now(),scope=args.scope,updates=args.updates,checks=checks,
            teacher_unchanged=True,student_encoder_unchanged=not encoder_changed,encoder_changed_tensors=encoder_changed,
            encoder_initial_sha256=encoder_before,encoder_final_sha256=tensor_digest(encoder.state_dict()),
            observation_normalizer_unchanged=True,
            critic_and_sigma_unchanged=True,changed_tensors=changed,initial_state_sha256=first_initial_sha,
            teacher_model_sha256=teacher_before,initial_model_sha256=tensor_digest(initial_model),
            physical_action_rnn_sha256=physics_hash.hexdigest() if args.runtime_only else None,
            scope_note=__doc__,sources={str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        atomic_json(args.output/'report.json',report)
        state.update(status='completed',finished=now());atomic_json(args.output/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now(),checks=checks);atomic_json(args.output/'status.json',state)
        raise
    finally:
        env.gym.destroy_sim(env.sim)


if __name__=='__main__':
    main()
