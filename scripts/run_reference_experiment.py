"""Run a gated short check, then one isolated teacher experiment.

The suite manifest is the single source of truth for GPU, batch, reward and data.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment

ROOT = Path(__file__).resolve().parents[1]


def training_command(spec, name, smoke=False):
    gpus = spec['gpus']
    world = len(gpus)
    command = [sys.executable]
    if world > 1:
        command += ['-m', 'torch.distributed.run', '--standalone', '--nnodes=1',
                    f'--nproc_per_node={world}']
    module = spec.get('training_module', 'isaacgymenvs.train')
    assert module in ['isaacgymenvs.train', 'scripts.train_wuji_student_actor_audited',
                      'scripts.train_wuji_population_student']
    command += ['-m', module, f"task={spec['task']}",
                f"hand={spec['hand']}", f"object={spec['object']}", f"train={spec['train']}",
                f"num_envs={spec['envs_per_rank']}", f'experiment={name}',
                f"max_iterations={3 if smoke else spec['epochs']}",
                f'multi_gpu={world>1}', 'headless=True', 'graphics_device_id=-1',
                'force_render=False', 'pipeline=gpu', 'num_subscenes=0', 'seed=20260921']
    command += spec.get('overrides', [])
    if smoke:command += spec.get('smoke_overrides', [])
    return command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    spec = json.loads(args.manifest.read_text())['experiments'][args.name]
    run = ROOT/'runs'/args.name
    run.mkdir(parents=True, exist_ok=True)
    lock = (run/'pipeline.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (run/'pipeline-status.json').exists():
        raise RuntimeError('Run already exists; do not silently overwrite or reset an experiment')
    # Enforce scheduling here as well as in the coordinator. A coordinator that
    # has not yet reloaded its code cannot start a dependent run prematurely.
    dependencies = spec.get('start_after_completed', [])
    while dependencies:
        states = {}
        for name in dependencies:
            path = ROOT/'runs'/name/'pipeline-status.json'
            states[name] = json.loads(path.read_text()).get('status') if path.exists() else 'missing'
        if all(status == 'completed' for status in states.values()):
            break
        if any(status in ('failed', 'cancelled_preflight_scheduling_race') for status in states.values()):
            raise RuntimeError('A required predecessor did not complete: ' + repr(states))
        print(json.dumps(dict(status='waiting_for_dependencies', time=now(), dependencies=states)), flush=True)
        time.sleep(30)
    expected_checkpoint = spec.get('source_checkpoint_sha256', spec.get('initial_checkpoint_sha256'))
    if expected_checkpoint:
        checkpoint_paths = [item.split('=', 1)[1] for item in spec.get('overrides', [])
                            if item.startswith('checkpoint=')]
        if len(checkpoint_paths) != 1 or hashlib.sha256(Path(checkpoint_paths[0]).read_bytes()).hexdigest() != expected_checkpoint:
            raise RuntimeError('Declared initial checkpoint hash does not match the training input')
    for gate_path in spec.get('behavioral_gates', []):
        gate = json.loads((ROOT/gate_path).read_text())
        if gate.get('status') != 'passed':
            raise RuntimeError('Required behavior check has not passed: ' + gate_path)
        if spec.get('termination_limits'):
            if gate.get('termination_limits') != spec['termination_limits']:
                raise RuntimeError('Termination runtime gate does not match declared thresholds')
            for key, value in spec['termination_limits'].items():
                setting = 'object.task.'+key+'='+str(value)
                if setting not in spec.get('overrides', []):
                    raise RuntimeError('Declared termination threshold missing from training command: '+setting)
        for source, sha in gate['sources'].items():
            if hashlib.sha256((ROOT/source).read_bytes()).hexdigest() != sha:
                raise RuntimeError('Behavior check source changed after validation: ' + source)
    if spec.get('geometry_dataset_gate'):
        gate_spec = spec['geometry_dataset_gate']
        identity = json.loads((ROOT/gate_spec['manifest']).read_text())
        checked_path = ROOT/gate_spec['runtime_report']
        checked = json.loads(checked_path.read_text())
        finished = json.loads(checked_path.with_name('status.json').read_text())
        if (identity['status'] != 'frozen' or identity['dataset'] != spec['object']
                or len(identity['instances']) != 3 or identity['independent_nominal_grasps'] != 1
                or checked['status'] != 'passed' or checked['dataset'] != spec['object']
                or checked['checks']['transitions'] != 10000 or min(checked['checks']['sampled_rows']) <= 0
                or not checked['authored_inertia_verified']
                or not checked.get('pose_frame_hand_base', False)
                or finished['status'] != 'completed' or finished['returncode'] != 0):
            raise RuntimeError('Geometry training data/runtime gate failed')
        for path, digest in identity['artifact_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Frozen geometry dataset changed: '+path)
        ready = dict(geometry_dataset=identity, runtime_gate=gate_spec['runtime_report'],
            caveat='Three geometries using one inherited grasp; no new grasp or hardware proof')
    elif spec.get('functional_dataset_gate'):
        gate_spec=spec['functional_dataset_gate']
        identity=json.loads((ROOT/gate_spec['manifest']).read_text())
        checked=json.loads((ROOT/gate_spec['runtime_report']).read_text())
        finished=json.loads((ROOT/gate_spec['runtime_report']).with_name('status.json').read_text())
        expected_train,expected_test=gate_spec.get('expected_counts',[20,1])
        if (identity['status']!='frozen' or identity['dataset']!=spec['object']
                or identity['train_count']!=expected_train or identity['test_count']!=expected_test
                or checked['status']!='passed' or checked['dataset']!=spec['object']
                or checked['train']!=expected_train or checked['test']!=expected_test
                or min(checked['checks']['sampled_rows'])<=0 or checked['checks']['transitions']!=10000
                or finished['status']!='completed' or finished['returncode']!=0):
            raise RuntimeError('Functional dataset training data/runtime gate failed')
        for name,digest in identity['artifact_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Frozen functional dataset changed: '+name)
        ready=dict(functional_dataset=identity,runtime_gate=gate_spec['runtime_report'],
                   caveat='Static functionality and correct training wiring, not held-out manipulation success')
    elif spec.get('normalizer_adaptation_gate'):
        gate_spec = spec['normalizer_adaptation_gate']
        identity = json.loads((ROOT/gate_spec['manifest']).read_text())
        policy_report_path = ROOT/gate_spec['report']
        policy_report = json.loads(policy_report_path.read_text())
        finished = json.loads((policy_report_path.parent/'status.json').read_text())
        if (identity['policy_sha256'] != expected_checkpoint
                or identity['changes'] != [dict(name='running_mean_std.running_mean', changed_elements=1)]
                or identity['index'] != 128
                or identity['new_nominal_damping'] != 3.
                or finished['status'] != 'completed' or finished['returncode'] != 0
                or policy_report['checkpoint_sha256'] != expected_checkpoint
                or policy_report['object'] != spec['object']
                or policy_report['hand'] != spec['hand']
                or policy_report['num_envs'] != 100
                or policy_report['first_cycle_strict'] < gate_spec['minimum_first_cycle_strict']):
            raise RuntimeError('Explicit normalizer-only warm start failed identity or independent policy gate')
        ready = dict(normalizer_adaptation=identity, report=gate_spec['report'],
                     first_cycle_strict=policy_report['first_cycle_strict'],
                     stable_full_all_endpoints=policy_report['stable_full_all_endpoints'],
                     note='Initialization capability gate only, not a declaration of task completion or calibrated hardware')
    elif spec.get('timed_gate'):
        gate_path = ROOT/spec['timed_gate']
        learned = json.loads(gate_path.read_text())
        completion = json.loads((gate_path.parent/'status.json').read_text())
        if (completion.get('status') != 'completed' or completion.get('returncode') != 0
                or learned['checkpoint_sha256'] != expected_checkpoint
                or learned['hand'] != spec['hand'] or learned['num_envs'] != 100
                or learned['stable_full_all_endpoints'] < 50):
            raise RuntimeError('Independent timed-command source checkpoint gate failed')
        ready = dict(timed_gate=spec['timed_gate'],
            checkpoint_sha256=learned['checkpoint_sha256'],
            stable_full_all_endpoints=learned['stable_full_all_endpoints'])
    elif spec.get('learned_gate'):
        learned=json.loads((ROOT/spec['learned_gate']).read_text())
        if learned['successful_trials'] != learned['envs'] or learned['strict_first_cycle_trials'] != learned['envs']:
            raise RuntimeError('Learned single-grasp physical gate failed')
        datasets=[]
        for gate in spec.get('dataset_gates',[]):
            result=json.loads((ROOT/gate).read_text())
            if result['status']!='completed' or result['counts']['train']<=0:
                raise RuntimeError('Official validated grasp data are incomplete')
            datasets.append(result)
        ready=dict(learned_gate=spec['learned_gate'],checkpoint_sha256=learned['checkpoint_sha256'],
                   successful_trials=learned['successful_trials'],validated_datasets=datasets)
        if spec.get('posture_gate'):
            posture=json.loads((ROOT/spec['posture_gate']).read_text())
            if posture['status']!='passed' or posture['splits']['train']['count']<=1:
                raise RuntimeError('Approved multi-grasp posture gate failed')
            for split,record in posture['splits'].items():
                path=ROOT/'caches/initial_grasp/wuji'/posture['dataset']/posture['instance']/split/'valid_grasps.npy'
                if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
                    raise RuntimeError('Posture-gated dataset changed')
            ready['posture_gate']=posture
    elif spec['hand'] == 'sharpa':
        ready = json.loads((ROOT/'runs/experiment-suite/sharpa-train-ready.json').read_text())
        if ready['train_objects'] != 30 or ready['train_grasps'] <= 0:
            raise RuntimeError('Incomplete official training dataset')
    else:
        ready = json.loads((ROOT/'runs/experiment-suite/wuji-replay/report.json').read_text())
        if ready['passed_environments'] != 32:
            raise RuntimeError('Reference replay gate failed')
    env = runtime_environment({'project':str(ROOT), 'python':sys.executable})
    env['CUDA_VISIBLE_DEVICES'] = ','.join(map(str,spec['gpus']))
    env['OMP_NUM_THREADS'] = '4'
    env['MKL_NUM_THREADS'] = '4'
    state = dict(status='preflight', started=now(), pid=os.getpid(), spec=spec, stages=[],
                 reward_source_sha256=hashlib.sha256((ROOT/'isaacgymenvs/tasks/artmanip.py').read_bytes()).hexdigest(),
                 gate=ready)
    state['code_sha256'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
        ['isaacgymenvs/tasks/artmanip.py', 'isaacgymenvs/tasks/wuji_acquisition.py',
         'isaacgymenvs/tasks/wuji_demo_aligned.py', 'scripts/wuji_pose_objective.py',
         'isaacgymenvs/tasks/wuji_timed_acquisition.py', 'isaacgymenvs/tasks/__init__.py',
         'scripts/wuji_endpoint_reward.py',
         'scripts/run_reference_experiment.py'] if (ROOT/name).exists()}
    atomic_json(run/'pipeline-status.json', state)
    (run/'pipeline.pid').write_text(str(os.getpid()))
    learning_stage = 'student_actor_rl' if spec.get('fixed_student_actor') else 'teacher'
    for stage_name, smoke in [('preflight', True), (learning_stage, False)]:
        name = args.name+'_smoke' if smoke else args.name
        command = training_command(spec,name,smoke)
        stage_env = dict(env)
        if spec.get('fixed_student_actor'):
            stage_env['WUJI_FIXED_STUDENT_AUDIT'] = str(ROOT/'runs'/name/'runtime-audit')
        with (run/f'{stage_name}.log').open('w') as log:
            process = subprocess.Popen(command,cwd=ROOT,env=stage_env,stdout=log,stderr=subprocess.STDOUT)
        stage = dict(name=stage_name,status='running',pid=process.pid,command=command,started=now())
        state['stages'].append(stage)
        state['status']=stage_name
        atomic_json(run/'pipeline-status.json',state)
        code = process.wait()
        stage.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
        if code:
            state.update(status='failed',finished=now())
            atomic_json(run/'pipeline-status.json',state)
            raise SystemExit(code)
        if spec.get('fixed_student_actor'):
            audit = json.loads((ROOT/'runs'/name/'runtime-audit/encoder-audit.json').read_text())
            expected_steps = (3 if smoke else spec['epochs']) * 32
            assert audit['training_returned'] and len(audit['environments']) == 1
            observed = audit['environments'][0]
            assert observed['control_steps'] == expected_steps
            assert observed['physics_transitions'] == expected_steps * spec['envs_per_rank']
            assert observed['student_sha256'] == spec['fixed_student_actor']['student_sha256']
            assert all(observed[key] for key in ['unchanged', 'all_parameters_frozen', 'encoder_in_eval', 'parameters_finite'])
            stage['fixed_encoder_audit'] = audit
        if smoke:
            checkpoint = ROOT/'runs'/name/'checkpoints/latest.json'
            record=json.loads(checkpoint.read_text())
            if record['epoch'] != 3 or record['world_size'] != len(spec['gpus']):
                raise RuntimeError('Short-run checkpoint does not match requested distributed run')
            if spec.get('fixed_learning_rate_preflight'):
                import torch
                payload=torch.load(ROOT/'runs'/name/'checkpoints/epoch_000003.pth',map_location='cpu')
                payload=payload[0] if 0 in payload else payload
                expected=float(spec['fixed_learning_rate_preflight'])
                rates=[float(group['lr']) for group in payload['optimizer']['param_groups']]
                if not rates or any(abs(rate-expected)>1e-12 for rate in rates):
                    raise RuntimeError('Fixed learning rate differs after actual PPO preflight: '+repr(rates))
                state['fixed_learning_rate_preflight']=dict(expected=expected,actual=rates,passed=True)
            if spec.get('max_preflight_kl') is not None:
                import math
                from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
                summary = EventAccumulator(str(ROOT/'runs'/name/'summaries'))
                summary.Reload()
                samples = summary.Scalars('info/kl') if 'info/kl' in summary.Tags()['scalars'] else []
                values = [float(sample.value) for sample in samples]
                limit = float(spec['max_preflight_kl'])
                passed = len(values) == 3 and all(math.isfinite(value) and 0 <= value <= limit for value in values)
                state['kl_preflight'] = dict(actual=values, maximum=limit, passed=passed)
                if not passed:
                    state.update(status='failed', finished=now(), error='Three-epoch PPO KL gate failed')
                    atomic_json(run/'pipeline-status.json', state)
                    raise RuntimeError('PPO update exceeds declared KL gate: '+repr(values))
            if spec.get('fixed_student_actor'):
                import torch
                source = torch.load(checkpoint_paths[0], map_location='cpu')
                source = source[0] if 0 in source else source
                learned = torch.load(ROOT/'runs'/name/'checkpoints/epoch_000003.pth', map_location='cpu')
                learned = learned[0] if 0 in learned else learned
                old_model, new_model = source['model'], learned['model']
                assert set(old_model) == set(new_model)
                assert all(torch.isfinite(value).all() for value in new_model.values())
                frozen = [key for key in old_model if key.startswith(('running_mean_std.', 'a2c_network.priv_encoder.'))]
                assert frozen and all(torch.equal(old_model[key], new_model[key]) for key in frozen)
                changed = [key for key in old_model if not torch.equal(old_model[key], new_model[key])]
                assert any(key.startswith(('a2c_network.actor_mlp.', 'a2c_network.a_rnn.', 'a2c_network.mu.')) for key in changed)
                assert any(key.startswith(('a2c_network.critic_mlp.', 'a2c_network.c_rnn.', 'a2c_network.value.')) for key in changed)
                state['student_actor_preflight'] = dict(actor_and_critic_updated=True, observation_stats_and_unused_teacher_encoder_frozen=True,
                                                        all_model_tensors_finite=True, changed_tensors=changed)
                if spec.get('controller_adapter') is not None:
                    adapter = spec['controller_adapter']
                    weight = 'a2c_network.controller_adapter.weight'
                    bias = 'a2c_network.controller_adapter.bias'
                    weight_changed = not torch.equal(old_model[weight], new_model[weight])
                    bias_changed = not torch.equal(old_model[bias], new_model[bias])
                    assert weight_changed == bool(adapter['enabled'])
                    assert bias_changed
                    state['controller_adapter_preflight'] = dict(enabled=bool(adapter['enabled']),
                        weight_changed=weight_changed,bias_changed=bias_changed,
                        all_initial_weights_zero=not bool(old_model[weight].count_nonzero()),
                        same_initialized_policy='Verified by separate real-physics runtime gate')
                if spec.get('training_population') is not None:
                    from scripts.audit_distillation_runtime import tensor_digest
                    population = json.loads((ROOT/'runs'/name/'runtime-audit/population-audit.json').read_text())
                    assert population['training_returned'] and len(population['records']) == 1
                    record = population['records'][0]
                    assert record['population'] == int(spec['training_population'])
                    assert record['rollout_transitions'] == 3 * 32 * spec['envs_per_rank']
                    assert record['first_model_sha256'] == tensor_digest(old_model)
                    if record['population'] == 1:
                        assert record['actual_input_ids'] == [50.0]
                        assert all(row['unused_rows_unchanged'] and row['first_row_changed']
                                   for row in record['parameter_rows'].values())
                    state['population_preflight'] = population
            if spec.get('max_preflight_on_policy_kl') is not None:
                import math
                audit = json.loads((ROOT/'runs'/name/'runtime-audit/kl-audit.json').read_text())
                epochs = audit['epochs']
                values = [row['on']['exact_mean'] for row in epochs]
                limit = float(spec['max_preflight_on_policy_kl'])
                passed = (audit['training_returned'] and [row['epoch'] for row in epochs] == [1, 2, 3]
                          and all(value is not None and math.isfinite(value) and -1e-10 <= value <= limit for value in values))
                state['on_policy_kl_preflight'] = dict(actual=values, maximum=limit, passed=passed,
                    definition='Exact Gaussian KL on original exploration-group samples against refreshed minibatch reference; excludes cross-group relabeling.')
                if not passed:
                    state.update(status='failed', finished=now(), error='Three-epoch exact on-policy KL gate failed')
                    atomic_json(run/'pipeline-status.json', state)
                    raise RuntimeError('Exact on-policy PPO KL exceeds declared gate: '+repr(values))
            if spec.get('normalizer_count_preflight'):
                import torch
                payload=torch.load(ROOT/'runs'/name/'checkpoints/epoch_000003.pth',map_location='cpu')
                payload=payload[0] if 0 in payload else payload
                initial=float(spec['normalizer_count_preflight'])
                count=float(payload['model']['running_mean_std.count'])
                if not initial<count<initial+10000000:
                    raise RuntimeError('Normalization count did not follow the declared initialization')
                state['normalizer_count_preflight']=dict(initial=initial,after3epochs=count,passed=True)
            if spec.get('input_normalizer_mode_preflight'):
                import torch
                mode = spec['input_normalizer_mode_preflight']
                assert mode in ('frozen', 'adaptive')
                source = torch.load(checkpoint_paths[0], map_location='cpu')
                source = source[0] if 0 in source else source
                trained = torch.load(ROOT/'runs'/name/'checkpoints/epoch_000003.pth', map_location='cpu')
                trained = trained[0] if 0 in trained else trained
                before, after = source['model'], trained['model']
                assert before.keys() == after.keys()
                assert all(torch.isfinite(value).all() for value in after.values())
                keys = [key for key in before if key.startswith('running_mean_std.')]
                assert keys
                same = all(torch.equal(before[key], after[key]) for key in keys)
                assert same == (mode == 'frozen'), (mode, keys)
                if mode == 'adaptive':
                    assert after['running_mean_std.count'] > before['running_mean_std.count']
                changed = [key for key in before if not torch.equal(before[key], after[key])]
                for prefixes in [('a2c_network.actor_mlp.', 'a2c_network.a_rnn.', 'a2c_network.mu.'),
                                 ('a2c_network.critic_mlp.', 'a2c_network.c_rnn.', 'a2c_network.value.')]:
                    assert any(key.startswith(prefixes) for key in changed), prefixes
                assert any(key.startswith('value_mean_std.') for key in changed)
                state['input_normalizer_preflight'] = dict(
                    mode=mode, input_statistics_equal_to_source=same,
                    input_count_before=float(before['running_mean_std.count']),
                    input_count_after=float(after['running_mean_std.count']),
                    actor_critic_and_value_statistics_updated=True, finite=True,
                    source_model_sha256=spec['source_checkpoint_sha256'])
        atomic_json(run/'pipeline-status.json',state)
    state.update(status='completed',finished=now())
    atomic_json(run/'pipeline-status.json',state)


if __name__ == '__main__':
    main()
