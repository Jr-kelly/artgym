"""Persistent five-minute checkpoint discovery with a durable evaluation queue.

One worker per host by default; an explicit GPU pool permits one per GPU. Scans
continue while evaluation runs. Training is never
stopped. Existing native evaluations are reused, and additional saved checkpoints
are evaluated from immutable CPU policy snapshots. Only stdlib is imported at
startup, so --ensure also works before the Isaac Gym runtime is activated.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path

# This file is also used as a direct daemon/worker entry point. Python then
# places scripts/ on sys.path, so later package imports need the project root.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import re
import subprocess
import sys
import time


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(data, indent=2))
    os.replace(temporary, path)


def pid_alive(pid):
    try:
        return Path('/proc', str(int(pid)), 'stat').read_text().split(') ')[1][0] != 'Z'
    except (OSError, ValueError, TypeError, IndexError):
        return False


def runtime_environment(config, gpu=None):
    env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONNOUSERSITE='1',
               OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', MAX_JOBS='2')
    runtime = str(Path(config['python']).parent.parent)
    env['PATH'] = runtime + '/bin:' + env.get('PATH', '')
    env['LD_LIBRARY_PATH'] = runtime + '/lib:' + env.get('LD_LIBRARY_PATH', '')
    project = config['project']
    env['PYTHONPATH'] = project + ':' + str(Path(project)/'rl_games')
    for key in ['RANK', 'LOCAL_RANK', 'WORLD_SIZE', 'LOCAL_WORLD_SIZE', 'MASTER_ADDR', 'MASTER_PORT']:
        env.pop(key, None)
    if gpu is not None:
        env['CUDA_VISIBLE_DEVICES'] = str(gpu)
    return env


def native_result(run, epoch):
    return read_json(Path(run) / 'evaluation' / f'epoch_{epoch:06d}' / 'result.json')


def reuse_native(job, result):
    if not result or result.get('status') != 'completed':
        return False
    # Profiles deliberately match the existing deterministic evaluation protocols.
    if 'execution_success_rate' not in result:
        return False
    job.update(status='completed', reused_native=True, result=result, finished=now())
    return True


def native_busy(run, epoch, discovered_time, wait_seconds=1200):
    run = Path(run)
    result = native_result(run, epoch)
    if result and result.get('status') in ('completed', 'failed', 'skipped'):
        return False
    pipeline = read_json(run / 'pipeline-status.json', {})
    watcher = pipeline.get('evaluation_watcher_pid')
    if watcher is None and pipeline.get('status') == 'running':
        watcher = pipeline.get('pid')
    if not pid_alive(watcher):
        return False
    status = read_json(run / 'evaluation/status.json', {})
    # Do not run two evaluations of one checkpoint if the native worker is active.
    if status.get('status') == 'running' and status.get('epoch') == epoch:
        return True
    # Recovery metadata is committed just before the native policy inbox entry.
    # Give that publication a short grace period to avoid a duplicate launch.
    if time.time() - discovered_time < 30:
        return True
    return ((run / 'evaluation/inbox' / f'epoch_{epoch:06d}.json').exists()
            and time.time() - discovered_time < wait_seconds)


def policy_snapshot(source, destination, expected_epoch=None):
    import torch
    source, destination = Path(source), Path(destination)
    before = source.stat()
    with source.open('rb') as stream:
        checkpoint = torch.load(stream, map_location='cpu')
    after = source.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise RuntimeError('Checkpoint changed while reading; retry next scan')
    state = checkpoint[0] if 0 in checkpoint else checkpoint
    epoch, frame = int(state['epoch']), int(state.get('frame', 0))
    if expected_epoch is not None and epoch != expected_epoch:
        raise ValueError('Checkpoint epoch differs from committed metadata')
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f'epoch_{epoch:06d}.pth'
    if not target.exists():
        temporary = target.with_name(target.name + f'.{os.getpid()}.tmp')
        with temporary.open('wb') as stream:
            torch.save({0: dict(model=state['model'], epoch=epoch, frame=frame)}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    return dict(epoch=epoch, frame=frame, policy_checkpoint=str(target.resolve()),
                policy_sha256=hashlib.sha256(target.read_bytes()).hexdigest())


def source_candidates(run):
    """Committed managed checkpoints first; legacy last/nn files are also supported."""
    run = Path(run)
    found = {}
    for directory, field in [('checkpoints', 'checkpoint'), ('evaluation/inbox', 'policy_checkpoint')]:
        for marker in sorted((run / directory).glob('epoch_*.json')):
            data = read_json(marker, {})
            if 'epoch' not in data:
                continue
            path = Path(data.get(field, str(marker.with_suffix('.pth'))))
            if path.exists():
                # Prefer the smaller native policy when it exists.
                found[int(data['epoch'])] = (path, data)
    if found:
        return [(path, data) for _, (path, data) in sorted(found.items(), reverse=True)]
    paths = list((run / 'nn').glob('*.pth'))
    last = run / 'last/model.pth'
    if last.exists():
        paths.append(last)
    return [(path, {}) for path in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)]


def evaluate_job(config, job_path):
    job_path = Path(job_path)
    job = read_json(job_path)
    result_path = Path(job['result_path'])
    run = Path(job['run'])
    root = Path(config['project'])
    output = result_path.parent
    output.mkdir(parents=True, exist_ok=True)
    profile = job['profile']
    aligned = profile == 'demo_aligned'
    evaluation = job.get('evaluation', {})
    instances = evaluation.get('instances', ['000'] if aligned else ['000', '010', '020'])
    result = dict(epoch=job['epoch'], frame=job['frame'], status='running', started=now(),
                  checkpoint=job['source'], policy_checkpoint=job['policy_checkpoint'],
                  policy_sha256=job['policy_sha256'], instances={}, seed=20260921,
                  randomized=not aligned, evaluation_scope=(
                      'One training grasp, repeated five times; no generalization claim' if aligned
                      else '22 test grasps of training geometries 000/010/020, five trials each'))
    result['evaluation_scope'] = evaluation.get('scope', result['evaluation_scope'])
    result['randomized'] = evaluation.get('randomized', not aligned)
    env = runtime_environment(config, job['gpu'])
    atomic_json(result_path, result)
    for attempt in range(1, 4):
        try:
            for instance in instances:
                summary = output / f'{instance}.json'
                if instance in result['instances']:
                    continue
                command = [config['python'], '-m', 'isaacgymenvs.eval_consecutive',
                           '--checkpoint', job['policy_checkpoint'], '--summary-output', str(summary),
                           '--task', evaluation.get('task', 'wuji_demo_aligned' if aligned else 'artmanip'),
                           '--hand', evaluation.get('hand', 'wuji_paper'),
                           '--object', evaluation.get('object', 'knife_wuji_demo_aligned' if aligned else 'knife_wuji_fingertip_eval'),
                           '--train', evaluation.get('train', 'wujiDemoAlignedSAPG' if aligned else 'wujiKnifeSAPG'),
                           '--instance-id', instance, '--grasp-split', evaluation.get('split', 'train' if aligned else 'test'),
                           '--episodes-per-grasp', str(evaluation.get('repeats', 5)),
                           '--max-steps', str(evaluation.get('max_steps', 1440 if aligned else 1200)),
                           '--headless', '--graphics-device-id', '-1', '--deterministic',
                           '--randomize', str(result['randomized']), '--seed', '20260921']
                command += evaluation.get('extra_args', [])
                if profile == 'acquisition' and '--pose-quality' not in command:
                    command.append('--pose-quality')
                atomic_json(output / f'{instance}-command.json', command)
                with (output / f'{instance}-attempt-{attempt}.log').open('w') as stream:
                    process = subprocess.Popen(command, cwd=root, env=env, stdout=stream,
                                               stderr=subprocess.STDOUT)
                    result.update(child_pid=process.pid, active_instance=instance, attempt=attempt)
                    atomic_json(result_path, result)
                    try:
                        code = process.wait(timeout=config.get('evaluation_timeout_seconds', 900))
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise
                    if code:
                        raise RuntimeError(f'{instance} evaluator exited with code {code}')
                data = read_json(summary)
                if not data or data.get('total_trials', 0) <= 0:
                    raise ValueError('Missing or empty evaluation summary')
                result['instances'][instance] = data
                atomic_json(result_path, result)
            trials = sum(r['total_trials'] for r in result['instances'].values())
            success = sum(r['successful_trials'] for r in result['instances'].values())
            result.update(status='completed', total_trials=trials, successful_trials=success,
                          execution_success_rate=success/trials,
                          mean_cycles=sum(r['mean_cycles']*r['total_trials'] for r in result['instances'].values())/trials)
            if all('consecutive_success_cycles_trials' in r for r in result['instances'].values()):
                from scripts.reference_metrics import aggregate_reference_metrics
                result['reference_metrics']=aggregate_reference_metrics(result['instances'])
            if all('pose_quality' in r for r in result['instances'].values()):
                qualities = [r['pose_quality'] for r in result['instances'].values()]
                strict = sum(q['strict_first_cycle_trials'] for q in qualities)
                stable = sum(q['stable_full_rollout_trials'] for q in qualities)
                result['pose_quality'] = dict(protocol='wuji_pose_quality_v1', total_trials=trials,
                    strict_first_cycle_trials=strict, stable_full_rollout_trials=stable,
                    strict_first_cycle_rate=strict/trials, stable_full_rollout_rate=stable/trials,
                    max_drift_m=.01, max_rotation_rad=.25)
            result.pop('error', None)
            break
        except Exception as error:
            result.update(error=repr(error), attempt=attempt)
            if attempt == 3:
                result['status'] = 'failed'
            else:
                time.sleep(10)
    result.update(finished=now(), child_pid=None)
    atomic_json(result_path, result)
    return 0 if result['status'] == 'completed' else 1


def inspect_training(run):
    run = Path(run)
    pipeline = read_json(run / 'pipeline-status.json', {})
    teacher = next((s for s in pipeline.get('stages', []) if s.get('name') == 'teacher'), {})
    pid = teacher.get('pid')
    alive = pid_alive(pid)
    result = dict(pipeline_status=pipeline.get('status'), teacher_pid=pid,
                  teacher_alive=alive, teacher_status=teacher.get('status'))
    path = run / 'teacher.log'
    if path.exists():
        with path.open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell()-24000))
            tail = stream.read().decode(errors='replace')
        matches = re.findall(r'epoch\s*:\s*([\d,]+)\s*/\s*([\d,]+)', tail)
        if matches:
            result.update(epoch=int(matches[-1][0].replace(',', '')),
                          max_epochs=int(matches[-1][1].replace(',', '')))
        result['log_updated'] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        result['stalled'] = alive and time.time() - path.stat().st_mtime > 900
    if teacher.get('status') == 'running' and not alive:
        result['alert'] = 'Training PID absent although pipeline says running'
    if result.get('stalled'):
        result['alert'] = 'No training log update for over 15 minutes'
    return result


class Monitor:
    def __init__(self, config, config_path):
        self.config = config
        self.config_path = str(Path(config_path).resolve())
        self.root = Path(config['state_dir'])
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_dir = self.root / 'jobs'
        self.jobs_dir.mkdir(exist_ok=True)
        self.cache = read_json(self.root / 'sources.json', {})
        self.processes = {}
        self.last_scan = None
        self.errors = []
        self.remote = None
        self.run_states = {}
        self.next_scan = time.monotonic()

    def job_path(self, name, epoch):
        return self.jobs_dir / f'{name}__epoch_{epoch:06d}.json'

    def save_job(self, job):
        atomic_json(self.job_path(job['name'], job['epoch']), job)

    def discover(self, spec):
        run = Path(spec['run'])
        for source, metadata in source_candidates(run):
            try:
                st = source.stat()
                signature = [st.st_ino, st.st_size, st.st_mtime_ns]
                previous = self.cache.get(str(source), {})
                epoch = metadata.get('epoch')
                if epoch is None and previous.get('signature') == signature:
                    epoch = previous['epoch']
                if epoch is not None and self.job_path(spec['name'], epoch).exists():
                    # Native evaluations may have been reused before an audit
                    # snapshot was made. Keep the documented immutable path
                    # available for independent physical-audit queues as well.
                    destination = run / 'evaluation/monitor/policies'
                    if not (destination / f'epoch_{epoch:06d}.pth').exists():
                        policy_snapshot(source, destination, epoch)
                    continue
                imported = native_result(run, epoch) if epoch is not None else None
                job = dict(name=spec['name'], run=str(run), source=str(source), profile=spec['profile'],
                           gpu=spec['gpu'], epoch=epoch, frame=metadata.get('frame', 0),
                           status='queued', discovered=now(), discovered_time=time.time())
                job['evaluation'] = spec.get('evaluation', {})
                if metadata.get('final') and spec.get('final_evaluation'):
                    job['evaluation'] = spec['final_evaluation']
                if imported and reuse_native(job, imported):
                    job['policy_checkpoint'] = imported.get('policy_checkpoint')
                    policy_snapshot(source, run / 'evaluation/monitor/policies', epoch)
                else:
                    job.update(policy_snapshot(source, run / 'evaluation/monitor/policies', epoch))
                    epoch = job['epoch']
                    # Legacy last and nn may contain the same epoch.
                    if self.job_path(spec['name'], epoch).exists():
                        self.cache[str(source)] = dict(signature=signature, epoch=epoch)
                        continue
                job['result_path'] = str(run / 'evaluation/monitor' / f'epoch_{epoch:06d}' / 'result.json')
                self.save_job(job)
                self.cache[str(source)] = dict(signature=signature, epoch=epoch)
            except Exception as error:
                self.errors.append(dict(source=str(source), error=repr(error), time=now()))

    def scan(self):
        scan_started = time.monotonic()
        self.errors = []
        for spec in self.config['runs']:
            try:
                self.run_states[spec['name']] = inspect_training(spec['run'])
                self.discover(spec)
            except Exception as error:
                self.errors.append(dict(run=spec['name'], error=repr(error), time=now()))
        atomic_json(self.root / 'sources.json', self.cache)
        self.last_scan = now()
        self.next_scan = scan_started + self.config.get('interval_seconds', 300)
        if self.config.get('remote_command'):
            try:
                # System ssh must use system OpenSSL, not the Conda runtime libs.
                ssh_env = {k:v for k,v in os.environ.items() if k != 'LD_LIBRARY_PATH'}
                output = subprocess.check_output(self.config['remote_command'], text=True,
                                                 timeout=25, env=ssh_env)
                self.remote = json.loads(output)
                atomic_json(self.root / 'remote-status.json', self.remote)
            except Exception as error:
                self.errors.append(dict(remote_error=repr(error), time=now()))
        self.publish()
        print('scan', self.last_scan, 'errors', len(self.errors), flush=True)

    def tick(self):
        self.processes = {pid: process for pid, process in self.processes.items()
                          if process.poll() is None}
        jobs = []
        active_jobs = []
        for path in sorted(self.jobs_dir.glob('*.json')):
            job = read_json(path)
            if job['status'] in ('completed', 'failed'):
                jobs.append(job)
                continue
            native = native_result(job['run'], job['epoch'])
            if job['status'] != 'running' and reuse_native(job, native):
                self.save_job(job)
            elif job['status'] == 'running':
                result = read_json(job['result_path'], {})
                if result.get('status') in ('completed', 'failed'):
                    job.update(status=result['status'], result=result, finished=result.get('finished', now()))
                    self.save_job(job)
                elif pid_alive(job.get('worker_pid')) or pid_alive(result.get('child_pid')):
                    active_jobs.append(job)
                else:
                    job.update(status='queued', recovery_note='Worker stopped; retry immutable snapshot')
                    self.save_job(job)
            jobs.append(job)
        gpu_pool = self.config.get('evaluation_gpus')
        busy_gpus = {job['gpu'] for job in active_jobs}
        available_gpus = [gpu for gpu in gpu_pool if gpu not in busy_gpus] if gpu_pool else []
        capacity = len(available_gpus) if gpu_pool else max(0, 1-max(len(active_jobs),len(self.processes)))
        if capacity:
            # FIFO prevents a slower experiment's first checkpoint from starving.
            priority = ((lambda j: (j['discovered_time'],j['name'],j['epoch']))
                        if self.config.get('evaluation_queue_order') == 'oldest_first'
                        else (lambda j: (-j['epoch'],j['name'])))
            # Explicit immutable checkpoints may be promoted without altering
            # discovery timestamps or discarding the historical queue.
            promoted = {(item['name'], int(item['epoch'])): index
                        for index, item in enumerate(self.config.get('priority_checkpoints', []))}
            def scheduling_key(job):
                selected = promoted.get((job['name'], int(job['epoch'])))
                return (0, selected) if selected is not None else (1, priority(job))
            for job in sorted(jobs, key=scheduling_key):
                if job['status'] != 'queued':
                    continue
                spec=next(s for s in self.config['runs'] if s['name']==job['name'])
                if any(not Path(p).exists() for p in spec.get('required_files', [])):
                    continue
                if native_busy(job['run'], job['epoch'], job['discovered_time']):
                    continue
                from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
                lease = None
                for gpu in (available_gpus if gpu_pool else [job['gpu']]):
                    lease = acquire_evaluation_gpu(gpu)
                    if lease is not None:
                        break
                if lease is None:
                    continue
                if gpu_pool:
                    available_gpus.remove(gpu)
                    job['gpu'] = gpu
                    # Publish assigned GPU before the worker reads its job file.
                    self.save_job(job)
                log = Path(job['result_path']).parent / 'worker.log'
                log.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with log.open('a') as stream:
                        process = subprocess.Popen(
                            [self.config['python'], str(Path(__file__).resolve()), '--config', self.config_path,
                             '--worker', str(self.job_path(job['name'], job['epoch']))],
                            cwd=self.config['project'], env=runtime_environment(self.config),
                            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                            start_new_session=True, pass_fds=(lease.fileno(),))
                finally:
                    lease.close()
                self.processes[process.pid] = process
                job.update(status='running', worker_pid=process.pid, started=now())
                self.save_job(job)
                print('evaluate', job['name'], job['epoch'], 'pid', process.pid, 'gpu',job['gpu'],flush=True)
                capacity -= 1
                if not capacity:break
        self.publish()

    def publish(self):
        jobs = [read_json(p) for p in self.jobs_dir.glob('*.json')]
        runs = {}
        for spec in self.config['runs']:
            current = [j for j in jobs if j['name'] == spec['name']]
            complete = [j for j in current if j['status'] == 'completed']
            latest = max(complete, key=lambda j: j['epoch']) if complete else None
            entry = dict(self.run_states.get(spec['name'], {}),
                         latest_discovered_epoch=max((j['epoch'] for j in current), default=None),
                         queued_epochs=sorted(j['epoch'] for j in current if j['status']=='queued'),
                         evaluating_epochs=[j['epoch'] for j in current if j['status']=='running'],
                         failed_epochs=[j['epoch'] for j in current if j['status']=='failed'],
                         evaluated_count=len(complete))
            entry['waiting_for_data']=[p for p in spec.get('required_files',[]) if not Path(p).exists()]
            if latest:
                result = latest['result']
                entry['latest_evaluation'] = {k: result.get(k) for k in [
                    'epoch','status','execution_success_rate','successful_trials','total_trials','mean_cycles','reference_metrics','pose_quality']}
                atomic_json(Path(spec['run']) / 'evaluation/monitor/latest.json', result)
            qualified = [j for j in complete if j['result'].get('pose_quality')]
            if qualified:
                def quality_rank(job):
                    quality = job['result']['pose_quality']
                    return (quality['stable_full_rollout_rate'], quality['strict_first_cycle_rate'],
                            job['result'].get('execution_success_rate', 0), -job['epoch'])
                best = max(qualified, key=quality_rank)
                entry['best_quality_evaluation'] = dict(epoch=best['epoch'],
                    policy_checkpoint=best['result']['policy_checkpoint'],
                    policy_sha256=best['result']['policy_sha256'],
                    pose_quality=best['result']['pose_quality'],
                    selection='Within this run: full-rollout stability, then first-cycle stability, then task completion. Candidate only, not a deployment approval.')
                atomic_json(Path(spec['run']) / 'evaluation/monitor/best-quality.json', entry['best_quality_evaluation'])
            successful = [j for j in complete if j['result'].get('successful_trials', 0)>0]
            if successful:
                first = min(successful, key=lambda j:j['epoch'])
                entry['first_successful_epoch'] = first['epoch']
            runs[spec['name']] = entry
        status = dict(monitor_pid=os.getpid(), heartbeat=now(), last_scan=self.last_scan,
                      interval_seconds=self.config.get('interval_seconds',300),
                      next_scan_in_seconds=max(0,round(self.next_scan-time.monotonic())),
                      runs=runs, errors=self.errors, remote=self.remote)
        atomic_json(self.root / 'status.json', status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--ensure', action='store_true')
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    if args.worker:
        raise SystemExit(evaluate_job(config, args.worker))
    root = Path(config['state_dir'])
    root.mkdir(parents=True, exist_ok=True)
    lock = (root / 'monitor.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        if not args.ensure:
            raise SystemExit('Monitor already running')
        print(json.dumps(read_json(root / 'status.json', {'status':'starting'})))
        return
    if args.ensure:
        # The child acquires its own lock; this lock closes when ensure exits.
        with (root / 'monitor.log').open('a') as stream:
            child = subprocess.Popen([config['python'], str(Path(__file__).resolve()),
                                      '--config', str(args.config.resolve())],
                                     cwd=config['project'], env=runtime_environment(config),
                                     stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        # Release before the interpreter starts the new process's main().
        fcntl.flock(lock, fcntl.LOCK_UN)
        print(json.dumps(dict(status='starting', monitor_pid=child.pid,
                              previous_status=read_json(root / 'status.json'))))
        return
    (root / 'monitor.pid').write_text(str(os.getpid())+'\n')
    monitor = Monitor(config, args.config)
    while True:
        if time.monotonic() >= monitor.next_scan:
            try:
                monitor.scan()
            except Exception as error:
                monitor.errors.append(dict(scan_error=repr(error),time=now()))
                monitor.next_scan=time.monotonic()+30
                print('scan error',repr(error),flush=True)
        monitor.tick()
        time.sleep(2)


if __name__ == '__main__':
    main()
