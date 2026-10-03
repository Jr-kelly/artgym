"""Continue a policy that actually crossed the loaded groove, retaining support as goal.

The history comparison uses fresh optimizers on both sides. Continuations restore
Adam/RNG. All four jobs draw a new noisy initial observation only at episode reset.
"""
import argparse, datetime, hashlib, json, os, pathlib, subprocess, time

p = argparse.ArgumentParser()
p.add_argument('--variant', choices=['wide30', 'slow6', 'wide6'], required=True)
p.add_argument('--gpu', type=int, required=True)
p.add_argument('--updates', type=int, required=True)
a = p.parse_args()
R = pathlib.Path(__file__).resolve().parents[2]
B = R / 'runs/support-pressure-20261003'
name = 'stronger-support-' + a.variant + '-support-timescale-v94'
job = B / 'jobs' / name
job.mkdir(parents=True, exist_ok=False)
original = json.loads((B / 'jobs/joint-noisier-continuation-v31/identity.json').read_text())
cmd = original['command'].copy()
weight = 'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth'
cmd[cmd.index('--resume') + 1] = weight
cmd[cmd.index('--output') + 1] = 'runs/support-pressure-20261003/train/' + name
cmd[cmd.index('--updates') + 1] = str(a.updates)
cmd.append('--resample-initial-estimates')
idx=cmd.index('--initial-estimate-scene');del cmd[idx:idx+2]
cmd += ['--override-initial-estimate-scene','research/support-pressure-20261003/staged-support-estimate-scene256-v88.json']
if a.variant in ['slow6','wide6']:cmd += ['--support-command-period','5']
if a.variant in ['wide30','wide6']:cmd += ['--reset-support-logstd','-.7']
env = dict(os.environ, PATH='/home/wangjiarui/artgym-runtime/bin:/usr/bin:/bin',
           LD_LIBRARY_PATH='/home/wangjiarui/artgym-runtime/lib', PYTHONUTF8='1',
           PYTHONNOUSERSITE='1', PYTHONPATH='.:rl_games', CUDA_VISIBLE_DEVICES=str(a.gpu),
           TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions', OMP_NUM_THREADS='4',
           MKL_NUM_THREADS='4', MAX_JOBS='2', PYTHONUNBUFFERED='1')
row = dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           command=cmd, launcher_pid=os.getpid(), gpu=a.gpu,
           initial_weight_sha256=hashlib.sha256((R / weight).read_bytes()).hexdigest(),
           scope='Training, all continuous TABLE episodes, not independent validation',
           reason='Strong750 supportlogit std .05275 gives <=.001392rad local exploration, below .002rad measurementnoise; actionmeans notsaturated. Test supportdecision timescale/exploration with originalphysics/actionspan and matched150updates; ordinary900 v89 reused baseline, no repeatedbaseline',
           optimizer='Restored full model/Adam/RNG; reset supportlogstd first16 and their exp_avg/exp_avg_sq only for wide variants; thumb and othermoments retained; new physicalepisodes',
           source_sha256={s: hashlib.sha256((R / s).read_bytes()).hexdigest() for s in
                          ['scripts/train_wuji_robust_residual.py', 'scripts/g2_continuous_scene.py',
                           'scripts/wuji_scheduled_thumb_reference.py','scripts/wuji_support_command_sampling.py','scripts/wuji_bounded_actor_update.py','scripts/g2_r800_policy.py']})
(job / 'identity.json').write_text(json.dumps(row, indent=2))
start = time.monotonic()
with (job / 'output.log').open('w') as log:
    child = subprocess.Popen(cmd, cwd=R, env=env, stdout=log, stderr=subprocess.STDOUT)
    row['child_pid'] = child.pid
    (job / 'identity.json').write_text(json.dumps(row, indent=2))
    child.wait()
row.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           exit_code=child.returncode, wall_seconds=time.monotonic() - start)
(job / 'result.json').write_text(json.dumps(row, indent=2))
print(json.dumps(row), flush=True)
