"""Resumable data generation → physical validation → SAPG teacher workflow.

Run with Isaac Gym's artgym Python. Lightning Grasp is a separate subprocess in
its CUDA 12 environment. A failed data-quality gate stops before teacher training.
Evaluation gates distillation; a teacher cannot be accepted based on epoch count.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import shlex

from scripts.wuji_training_launch import training_plan, teacher_command

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=ROOT/'runs/wuji_knife_paper_sapg')
    parser.add_argument('--lygra-python', type=Path, default=ROOT/'tmp/lygra-env/bin/python')
    parser.add_argument('--outer', type=int, default=256)
    parser.add_argument('--inner', type=int, default=128)
    budget=parser.add_mutually_exclusive_group()
    budget.add_argument('--epochs', type=int, help='Explicit number of global update epochs')
    budget.add_argument('--total-steps', type=int, help='Global transitions across all GPUs; default 2,048,000,000')
    parser.add_argument('--gpus', type=int, choices=(1,2,4), default=1)
    parser.add_argument('--envs-per-gpu', type=int, default=2560)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--weights-only', action='store_true', help='Warm start model/normalization, reset optimizer/counters; use when GPU count changes')
    parser.add_argument('--dry-run', action='store_true', help='Print resolved launch and budget without starting work')
    parser.add_argument('--data-only', action='store_true')
    parser.add_argument('--student-updates', type=int, default=10000)
    parser.add_argument('--fingertip-filter', action='store_true', help='Use the separately filtered dataset; never regenerate original candidates')
    parser.add_argument('--periodic-eval', action='store_true', help='Evaluate periodic teacher snapshots during training')
    parser.add_argument('--eval-gpu', type=int, default=3, help='Visible GPU index shared by the background evaluator')
    args = parser.parse_args()
    os.chdir(ROOT)
    run = args.run_dir.resolve()
    dataset = 'knife_wuji_fingertip' if args.fingertip_filter else 'knife_wuji_paper'
    plan=training_plan(args.gpus,args.envs_per_gpu,args.total_steps,args.epochs)
    command=teacher_command(sys.executable,dataset,run.name,plan,
                            args.checkpoint.resolve() if args.checkpoint else None,args.weights_only)
    if args.dry_run:
        print(json.dumps(plan,indent=2));print(shlex.join(command));return
    if not args.data_only:
        # Separate process preserves Isaac Gym's import-before-torch requirement.
        visible=int(subprocess.check_output([sys.executable,'-c','import torch; print(torch.cuda.device_count())'],text=True).strip())
        if visible<args.gpus:
            raise RuntimeError(f'Requested {args.gpus} GPUs but this session sees {visible}; allocate GPUs before launching')
        if args.periodic_eval and not 0 <= args.eval_gpu < visible:
            raise ValueError(f'--eval-gpu {args.eval_gpu} is outside {visible} visible GPUs')
    if args.fingertip_filter and run.name == 'wuji_knife_paper_sapg':
        raise ValueError('Use a separate --run-dir for the filtered experiment')
    run.mkdir(parents=True, exist_ok=True)
    if (run/'pipeline-status.json').exists():
        raise ValueError('Run directory already has pipeline state; use a new --run-dir and an explicit checkpoint')
    lock = (run/'pipeline.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (run/'pipeline.pid').write_text(str(os.getpid())+'\n')
    environment = dict(os.environ, PYTHONHASHSEED='20260920', PYTHONUNBUFFERED='1', MAX_JOBS='2')
    stages = []
    state = dict(pid=os.getpid(), started=datetime.now(timezone.utc).isoformat(), stages=stages,
                 dataset=dataset,training_plan=plan,geometry_manifest=json.loads((ROOT/'assets/objects'/dataset/'manifest.json').read_text()))

    def save():
        temporary = run/'pipeline-status.tmp'
        temporary.write_text(json.dumps(state, indent=2))
        temporary.replace(run/'pipeline-status.json')

    def stage(name, command):
        record = dict(name=name, command=list(map(str,command)), started=datetime.now(timezone.utc).isoformat(), status='running')
        stages.append(record)
        state['status'] = name
        save()
        print('START',name,flush=True)
        with (run/(name+'.log')).open('a') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
            record['pid'] = process.pid
            save()
            code = process.wait()
        record.update(finished=datetime.now(timezone.utc).isoformat(), returncode=code,
                      status='completed' if code==0 else 'failed')
        save()
        if code:
            raise RuntimeError(f'{name} failed ({code}); see {run/(name+".log")}')
        print('DONE',name,flush=True)

    def evaluate(name, checkpoint, instance, student=None, video=None):
        command = [sys.executable, '-m', 'isaacgymenvs.eval_consecutive', '--checkpoint', str(checkpoint),
                   '--summary-output', str(run/(name+'.json')),
                   '--hand', 'wuji_paper', '--object', dataset+'_eval', '--train', 'wujiKnifeSAPG',
                   '--instance-id', instance, '--grasp-split', 'test' if instance=='000' else 'valid',
                   '--episodes-per-grasp', '1' if video else '5', '--max-steps', '1200', '--headless',
                   '--deterministic', '--randomize', 'True', '--seed', '20260921']
        if student:
            command.extend(['--student-artifact', str(student)])
        if video:
            command.extend(['--save-video', str(run/'student-demo.mp4'), '--video-env-index', str(video['best_grasp_index'])])
        stage(name, command)
        source = run/(name+'.json')
        result = json.loads(source.read_text())
        result.update(checkpoint=str(checkpoint), student_artifact=str(student) if student else None,
                      seed=20260921, randomized=True)
        (run/(name+'.json')).write_text(json.dumps(result,indent=2))
        return result

    def require_cycles(report, name):
        if report['best_consecutive_success_cycles'] < 1:
            raise RuntimeError(f'{name}: no grasp averages a complete cycle over five trials; further training is required')

    try:
        for instance in ([] if args.fingertip_filter else state['geometry_manifest']['train_ids']+state['geometry_manifest']['test_ids']):
            stage('generate-'+instance, [str(args.lygra_python), '-m', 'scripts.generate_functional_wuji_grasps',
                              '--instances', instance, '--count', '1000', '--field-samples', '80000',
                              '--outer', str(args.outer), '--inner', str(args.inner), '--max-batches', '4000'])
            stage('validate-'+instance, [sys.executable, '-m', 'scripts.validate_paper_grasps', '--instances', instance])
        stage('dataset-preflight', [sys.executable, '-m', 'scripts.filter_wuji_fingertip_grasps', 'check'] if args.fingertip_filter
              else [sys.executable, '-m', 'scripts.validate_paper_grasps', '--check-training-ready'])
        if not args.data_only:
            watcher = None
            if args.periodic_eval:
                (run/'evaluation').mkdir(exist_ok=True)
                watcher_log = (run/'evaluation'/'watcher.log').open('a')
                watcher = subprocess.Popen([sys.executable, '-u', '-m', 'scripts.watch_wuji_training',
                    '--run-dir', str(run), '--dataset', dataset, '--gpu', str(args.eval_gpu)],
                    stdout=watcher_log, stderr=subprocess.STDOUT, env=environment)
                watcher_log.close()
                state['evaluation_watcher_pid'] = watcher.pid
                save()
            try:
                stage('teacher', command)
            finally:
                if watcher is not None:
                    from rl_games.common.checkpoint_schedule import atomic_json
                    atomic_json(run/'evaluation'/'training-finished.json', dict(finished=datetime.now(timezone.utc).isoformat()))
                    watcher.wait(timeout=3000)
                    if watcher.returncode:
                        raise RuntimeError('Periodic evaluation watcher failed; inspect evaluation/watcher.log')
            checkpoint = run/'nn'/f'{run.name}.pth'
            if args.periodic_eval:
                if not (run/'evaluation'/'best.pth').exists():
                    raise RuntimeError('No successful periodic evaluation; inspect evaluation/history.jsonl')
                checkpoint = (run/'evaluation'/'best.pth').resolve()
            if not checkpoint.exists():
                raise FileNotFoundError(f'Training did not produce its best-reward checkpoint at {checkpoint}')
            report = evaluate('teacher-anchor', checkpoint, '000')
            require_cycles(report, 'teacher-anchor')
            # All selection decisions use training-geometry grasps, never held-out objects.
            student = run/'student'/'proprio_only.pth'
            stage('distill', [sys.executable, '-m', 'isaacgymenvs.distill', '--checkpoint', str(checkpoint),
                             '--train', 'wujiKnifeSAPG', '--hand', 'wuji_paper', '--object', dataset,
                             '--num-envs', '256', '--updates', str(args.student_updates), '--rollout-steps', '16',
                             '--cosine-coef', '0', '--student-init', 'random', '--grasp-split', 'train',
                             '--headless', '--save-every-updates', '500', '--output-checkpoint', str(student)])
            report = evaluate('student-anchor', checkpoint, '000', student)
            for instance in state['geometry_manifest']['test_ids']:
                evaluate('teacher-heldout-'+instance, checkpoint, instance)
                evaluate('student-heldout-'+instance, checkpoint, instance, student)
            require_cycles(report, 'student-anchor')
            evaluate('student-video', checkpoint, '000', student, video=report)
        state['status'] = 'data_ready' if args.data_only else 'sim_pipeline_finished_hardware_calibration_pending'
    except BaseException as error:
        state['status'] = 'failed'
        state['error'] = str(error)
        raise
    finally:
        state['updated'] = datetime.now(timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
