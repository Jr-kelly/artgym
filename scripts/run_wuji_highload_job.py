"""Run one authorized local experiment and persist its identity/result."""
import argparse,subprocess,os,json,datetime,hashlib
from pathlib import Path
from scripts.record_wuji_highload_goal import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--gpu',type=int,default=0);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();R=Path(__file__).resolve().parents[1];d=R/'runs/highload-20261005/jobs'/a.name;d.mkdir(parents=True,exist_ok=False);cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command;assert cmd
 env=os.environ.copy();env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH=str(R)+':'+str(R/'rl_games'),PYTHONNOUSERSITE='1',CUDA_VISIBLE_DEVICES=str(a.gpu),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',MAX_JOBS='2',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',PYTHONUNBUFFERED='1')
 source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
 patch=subprocess.check_output(['git','diff','HEAD','--','scripts'],cwd=R);(d/'source.patch').write_bytes(patch)
 source_files=['scripts/wuji_scheduled_thumb_reference.py','scripts/wuji_initial_table_prior.py','scripts/wuji_joint_deflection_acquisition.py','scripts/wuji_known_acquisition_prefix.py','scripts/replay_wuji_support_commands.py','scripts/export_wuji_legal_replay.py','scripts/g2_continuous_scene.py','scripts/g2_r800_policy.py','scripts/g2_batched_r800.py','scripts/wuji_known_controller.py','scripts/wuji_bounded_motor_residual.py','scripts/run_g2_robust_demo.py','scripts/train_wuji_robust_residual.py']
 if '-m' in cmd:source_files.append(cmd[cmd.index('-m')+1].replace('.','/')+'.py')
 source_sha256={path:hashlib.sha256((R/path).read_bytes()).hexdigest() for path in source_files if (R/path).is_file()}
 input_sha256={}
 for i,value in enumerate(cmd[:-1]):
  if value in ['--plan','--motor-plan','--localization','--knife-spec','--knife-asset','--thumb-reference-override','--support-pressure-config','--support-acquisition-config','--proprioceptive-pressure-config','--checkpoint','--residual-checkpoint','--initialize-model-from','--resume','--thumb-reference','--reference','--initial-estimate-scene','--override-initial-estimate-scene','--scene','--grasp-plan','--acquisition-path','--table-calibration','--handover-calibration','--geometry-schedule','--training-geometry-schedule','--asset-registry','--training-asset-registry']:
   path=Path(cmd[i+1]);path=path if path.is_absolute() else R/path
   if path.is_file():input_sha256[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 with (d/'output.log').open('w') as f:
  child=subprocess.Popen(cmd,env=env,cwd=R,stdout=f,stderr=subprocess.STDOUT);info=dict(command=cmd,pid=child.pid,launcher_pid=os.getpid(),gpu=a.gpu,source_commit=source_commit,source_patch_sha256=hashlib.sha256(patch).hexdigest(),source_sha256=source_sha256,input_sha256=input_sha256,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'identity.json').write_text(json.dumps(info,indent=2));record('traction_job_started',active_job=dict(name=a.name,machine='local',pid=child.pid,gpu=a.gpu,source_commit=source_commit,source_patch_sha256=hashlib.sha256(patch).hexdigest(),source_sha256=source_sha256,input_sha256=input_sha256,start_utc=info['start_utc']),config=info,evidence=str(d.relative_to(R)),next='Inspect actual result and persist conclusion; no simulation/hardware success inferred from process startup');code=child.wait()
 info.update(exit_code=code,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'result.json').write_text(json.dumps(info,indent=2));record('traction_job_closed',closed_job=dict(name=a.name,machine='local'),config=info,evidence=str(d.relative_to(R)),next='Evaluate actual behavior/geometry and decide next intervention');print(json.dumps(info));raise SystemExit(code)
if __name__=='__main__':main()
