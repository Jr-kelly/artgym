"""Distill an explicitly identified teacher with independent gates and real preflight."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--after-run", help="Wait for this same-host experiment to finish before preflight")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    assert Path(spec["run"]).name == spec["run"]
    assert spec["updates"] > 0 and spec["preflight_updates"] >= 5
    assert float(spec.get("cosine_coef", 0.1)) >= 0
    module = spec.get('distill_module', 'isaacgymenvs.distill')
    assert module in ['isaacgymenvs.distill', 'scripts.distill_wuji_variable_student']
    teacher = ROOT/spec["teacher"]
    teacher_hash = hashlib.sha256(teacher.read_bytes()).hexdigest()
    assert teacher_hash == spec["teacher_sha256"]
    if spec.get('controller_state_runtime_gate'):
        assert spec['task'] == 'wuji_acquisition_bridge3_controller_state'
        gate = ROOT / spec['controller_state_runtime_gate']
        checked = json.loads(gate.read_text())
        finished = json.loads(gate.with_name('status.json').read_text())
        assert checked['status'] == 'passed' and checked['transitions'] >= 10000
        assert finished['status'] == 'completed' and finished['returncode'] == 0
        assert checked['unchanged_teacher_observations'] and checked['frozen_teacher_unchanged']
        assert not checked['current_privileged_object_inputs']
        assert checked['controller_mapping_exact'] and checked['existing_student_input_prefix_exact']
        for source, digest in checked['sources'].items():
            assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest() == digest
    if spec.get('teacher_latent_mix_initial', 0.0):
        assert 0 < spec['teacher_latent_mix_initial'] <= 1
        assert 0 < spec['teacher_latent_mix_updates'] < spec['updates']
        assert spec.get('teacher_rollout_updates', 0) == 0
        gate = ROOT / spec['latent_mix_runtime_gate']
        checked = json.loads(gate.read_text())
        check_status = json.loads((gate.parent / 'status.json').read_text())
        assert check_status['status'] == 'completed' and check_status['returncode'] == 0
        assert checked['status'] == 'passed' and checked['physics_transitions'] >= 256
        assert checked['action_and_rnn_exact'] and checked['supervision_hook_removed']
        for source, digest in checked['sources'].items():
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
    if spec.get('student_rollout_eval_mode', False):
        gate = ROOT / spec['rollout_mode_runtime_gate']
        checked = json.loads(gate.read_text())
        check_status = json.loads((gate.parent / 'status.json').read_text())
        assert check_status['status'] == 'completed' and check_status['returncode'] == 0
        assert checked['status'] == 'passed' and checked['deployment_actions_and_rnn_match_exactly']
        for source, digest in checked['sources'].items():
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
    if spec.get('action_loss_coef', 0.0):
        gate = ROOT / spec['action_loss_runtime_gate']
        checked = json.loads(gate.read_text())
        check_status = json.loads((gate.parent / 'status.json').read_text())
        assert check_status['status'] == 'completed' and check_status['returncode'] == 0
        assert checked['status'] == 'passed' and checked['physics_transitions'] >= 256
        assert checked['max_teacher_mean_action_error'] < 5e-5
        for source in ['isaacgymenvs/utils/distill_action_loss.py', 'isaacgymenvs/distill.py']:
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == checked['sources'][source]
    student_initialization = None
    if spec.get('student_checkpoint'):
        student_initialization = ROOT / spec['student_checkpoint']
        assert hashlib.sha256(student_initialization.read_bytes()).hexdigest() == spec['student_checkpoint_sha256']
    for item in spec["evaluation_gates"]:
        path = ROOT/item["report"]
        report = json.loads(path.read_text())
        status = json.loads((path.parent/"status.json").read_text())
        assert status["status"] == "completed" and status["returncode"] == 0
        assert report["checkpoint_sha256"] == teacher_hash
        assert report["hand"] == spec["hand"]
        assert report["num_envs"] == item.get("num_envs", 100)
        for key, minimum in item["minimum_counts"].items():
            assert report[key] >= minimum, (key, report[key], minimum)
        for split in item.get('splits', []):
            rows = report['records'][split['start']:split['stop']]
            assert len(rows) == split['stop'] - split['start']
            for key, minimum in split['minimum_counts'].items():
                assert sum(bool(row[key]) for row in rows) >= minimum
    run = ROOT/"runs"/spec["run"]
    run.mkdir(exist_ok=True, parents=True)
    lock = (run/"pipeline.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (run/"pipeline-status.json").exists():
        raise RuntimeError("Preserve existing student experiments; use a new run name")
    state = dict(status="preflight", started=now(), spec=spec, stages=[],
        spec_sha256=hashlib.sha256(args.spec.read_bytes()).hexdigest(),
        sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            "scripts/run_wuji_student_from_spec.py", "isaacgymenvs/distill.py",
            "scripts/audit_distillation_runtime.py", "isaacgymenvs/tasks/wuji_timed_acquisition.py",
            "isaacgymenvs/utils/distill_rollout_utils.py", "isaacgymenvs/utils/distill_action_loss.py"]})
    state_path = run/"pipeline-status.json"
    if module == 'scripts.distill_wuji_variable_student':
        source = 'scripts/distill_wuji_variable_student.py'
        state['sources'][source] = hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
    atomic_json(state_path, state)
    if args.after_run:
        if Path(args.after_run).name != args.after_run:
            raise ValueError('Predecessor must be a run name')
        predecessor = ROOT/'runs'/args.after_run/'pipeline-status.json'
        deadline = time.monotonic()+14400
        state.update(status='waiting_for_predecessor', after_run=args.after_run)
        atomic_json(state_path, state)
        while time.monotonic() < deadline:
            previous = json.loads(predecessor.read_text())
            if previous['status'] == 'completed':
                break
            if previous['status'] in ['failed', 'stopped_reallocated', 'stopped_posture_gate']:
                state.update(status='failed', finished=now(), error='Predecessor did not complete')
                atomic_json(state_path, state)
                raise RuntimeError(state['error'])
            time.sleep(30)
        else:
            state.update(status='failed', finished=now(), error='Predecessor wait exceeded four hours')
            atomic_json(state_path, state)
            raise RuntimeError(state['error'])
    env = runtime_environment(dict(project=str(ROOT), python=sys.executable), spec["gpu"])
    for stage, updates in [("preflight", spec["preflight_updates"]), ("distilling", spec["updates"])]:
        out = run/"preflight" if stage == "preflight" else run
        out.mkdir(exist_ok=True)
        cmd = [sys.executable, "-m", module,
            "--checkpoint", str(teacher), "--task", spec["task"], "--hand", spec["hand"],
            "--object", spec["object"], "--train", "wujiAcquisitionSAPG",
            "--num-envs", str(spec["num_envs"]), "--updates", str(updates),
            "--rollout-steps", str(spec["rollout_steps"]), "--lr", str(spec["lr"]),
            "--cosine-coef", str(spec.get("cosine_coef", 0.1)), "--deterministic", "--expl-block-idx", "0",
            "--headless", "--graphics-device-id", "-1", "--save-every-updates",
            "1" if stage == "preflight" else str(spec["save_every"]),
            "--save-best-after-updates", str(spec["save_every"]), "--grasp-split", "train",
            "--seed", str(spec["seed"]), "--output-checkpoint", str(out/"student.pth"),
            "--audit-output-dir", str(out/"runtime-audit")]
        teacher_updates = spec.get('teacher_rollout_updates', 0)
        if stage == 'preflight' and teacher_updates:
            teacher_updates = 2  # Exercise both policies in the real preflight.
        cmd += ['--teacher-rollout-updates', str(teacher_updates)]
        if spec.get('action_loss_coef', 0.0):
            cmd += ['--action-loss-coef', str(spec['action_loss_coef'])]
        if spec.get('student_rollout_eval_mode', False):
            cmd += ['--student-rollout-eval-mode']
        if spec.get('replay_capacity', 0):
            cmd += ['--replay-capacity', str(spec['replay_capacity']),
                    '--replay-fraction', str(spec['replay_fraction'])]
            if spec.get('replay_supervision'):
                cmd += ['--replay-supervision', spec['replay_supervision']]
        if student_initialization is not None:
            cmd += ['--student-checkpoint', str(student_initialization)]
        if spec.get('teacher_latent_mix_initial', 0.0):
            cmd += ['--teacher-latent-mix-initial', str(spec['teacher_latent_mix_initial']),
                    '--teacher-latent-mix-updates', str(spec['teacher_latent_mix_updates'])]
        with (out/"distillation.log").open("w") as log:
            child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT)
        row = dict(name=stage, status="running", pid=child.pid, command=cmd, started=now())
        state["status"] = stage
        state["stages"].append(row)
        atomic_json(state_path, state)
        code = child.wait()
        row.update(returncode=code, finished=now())
        if code == 0:
            audit = json.loads((out/"runtime-audit/runtime-audit.json").read_text())
            assert audit['arguments']['cosine_coef'] == float(spec.get('cosine_coef', 0.1))
            assert audit['arguments']['lr'] == float(spec['lr'])
            if module == 'scripts.distill_wuji_variable_student':
                assert audit['command_clock_kind'] == 'sampled_deadline'
                assert audit['command_duration_steps'] == [60, 150]
                assert min(audit['training_grasp_step_counts']) > 0
                assert min(audit['rescheduled_duration_counts'].values()) > 0
                if spec.get('controller_state_runtime_gate'):
                    assert audit['controller_state_inputs']
                    assert audit['student_observation_dim'] == 2076
                    assert audit['controller_input_checks'] == audit['clock_observed_transitions']
            if not (audit["status"] == "verified" and audit["completed_updates"] == updates
                    and audit["command_period_steps"] == 60 and audit["clock_switches"] > 0
                    and audit["clock_observed_transitions"] == updates*spec["rollout_steps"]*spec["num_envs"]):
                code = 1
                row["error"] = "Frozen model, actuator, perturbation or command-clock audit failed"
            expected_teacher = teacher_updates*spec['rollout_steps']*spec['num_envs']
            expected_student = (updates-teacher_updates)*spec['rollout_steps']*spec['num_envs']
            expected_counts = dict(teacher=expected_teacher, student=expected_student)
            if spec.get('teacher_latent_mix_initial', 0.0):
                mixed_updates = min(updates, spec['teacher_latent_mix_updates'])
                mixed_transitions = mixed_updates * spec['rollout_steps'] * spec['num_envs']
                expected_counts['mixed'] = mixed_transitions
                expected_counts['student'] -= mixed_transitions
                expected_sum = sum(spec['teacher_latent_mix_initial'] * (1-i/spec['teacher_latent_mix_updates'])
                                   for i in range(mixed_updates)) * spec['rollout_steps'] * spec['num_envs']
                if abs(audit.get('teacher_fraction_transition_sum', -1)-expected_sum) > 1e-6 * max(1, expected_sum):
                    code = 1
                    row['error'] = 'Actual privileged mixture weights differ from the schedule'
            if spec.get('student_rollout_eval_mode', False):
                if audit.get('student_rollout_module_modes') != dict(training=0, evaluation=expected_student):
                    code = 1
                    row['error'] = 'Actual student rollout module modes differ from declared evaluation mode'
            if audit.get('rollout_action_transitions') != expected_counts:
                code = 1
                row['error'] = 'Actual teacher/student rollout counts differ from the declared schedule'
            if spec.get('replay_capacity', 0):
                replay = json.loads((out/'runtime-audit/replay-report.json').read_text())
                assert replay['writes'] == expected_student
                assert replay['sampled_transitions'] == expected_student-spec['num_envs']
                assert replay['capacity'] == spec['replay_capacity']
                assert replay['fraction'] == spec['replay_fraction'] and replay['private_rng']
                if spec.get('replay_supervision'):
                    source = spec['replay_supervision']
                    assert replay['supervision_source'] == source
                    counts = dict(past=0, current=0)
                    counts[source] = expected_student-spec['num_envs']
                    assert replay['supervised_transitions'] == counts
                assert replay['samples_older_than_60_steps'] > 0
                if stage == 'distilling':
                    assert replay['samples_older_than_150_steps'] > 0
                    assert replay['size'] == spec['replay_capacity']
                row['replay_verified'] = replay
        row["status"] = "completed" if code == 0 else "failed"
        if code:
            state.update(status="failed", finished=now())
            atomic_json(state_path, state)
            raise SystemExit(code)
        atomic_json(state_path, state)
        if stage == 'preflight' and spec.get('paired_preflight_peer'):
            peer_name = spec['paired_preflight_peer']
            assert Path(peer_name).name == peer_name
            peer = ROOT/'runs'/peer_name
            deadline = time.monotonic() + 1800
            while time.monotonic() < deadline:
                peer_path = peer/'pipeline-status.json'
                other = json.loads(peer_path.read_text()) if peer_path.exists() else {}
                if other.get('status') == 'failed':
                    raise RuntimeError('Paired preflight failed: ' + peer_name)
                finished_preflight = any(s['name'] == 'preflight' and s['status'] == 'completed'
                                         for s in other.get('stages', []))
                if finished_preflight:
                    break
                time.sleep(10)
            else:
                raise TimeoutError('Paired preflight did not complete in30minutes')
            other_audit = json.loads((peer/'preflight/runtime-audit/runtime-audit.json').read_text())
            own_audit = json.loads((run/'preflight/runtime-audit/runtime-audit.json').read_text())
            for key in ['actor_and_normalizers_before', 'teacher_encoder_before']:
                assert own_audit[key] == other_audit[key], key
            assert own_audit['student_initialization']['observed_tensor_digest'] == other_audit['student_initialization']['observed_tensor_digest']
            import numpy as np
            with np.load(run/'preflight/runtime-audit/initial_states.npz') as own, np.load(peer/'preflight/runtime-audit/initial_states.npz') as theirs:
                for key in own.files:
                    assert np.array_equal(own[key], theirs[key]), ('Initial preflight states differ', key)
            state['paired_initialization_verified'] = dict(peer=peer_name, checked=now(),
                same_teacher_actor_normalizers_student_and_initial_states=True)
            atomic_json(state_path, state)
    state.update(status="completed", finished=now())
    atomic_json(state_path, state)


if __name__ == "__main__":
    main()
