"""Run one authorized local experiment and persist its identity/result."""
import argparse,subprocess,os,json,datetime,hashlib
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--gpu',type=int,default=0);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();R=Path(__file__).resolve().parents[1];d=R/'runs/antirotation-grasp-20261004/jobs'/a.name;d.mkdir(parents=True,exist_ok=False);cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command;assert cmd
 env=os.environ.copy();env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH=str(R)+':'+str(R/'rl_games'),PYTHONNOUSERSITE='1',CUDA_VISIBLE_DEVICES=str(a.gpu),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',MAX_JOBS='2',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',PYTHONUNBUFFERED='1')
 with (d/'output.log').open('w') as f:
  child=subprocess.Popen(cmd,env=env,cwd=R,stdout=f,stderr=subprocess.STDOUT);info=dict(command=cmd,pid=child.pid,launcher_pid=os.getpid(),gpu=a.gpu,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'identity.json').write_text(json.dumps(info,indent=2));record('antirotation_job_started',active_job=dict(name=a.name,machine='local',pid=child.pid,gpu=a.gpu,start_utc=info['start_utc']),config=info,evidence=str(d.relative_to(R)),next='Inspect actual result and persist conclusion; no simulation/hardware success inferred from process startup');code=child.wait()
 info.update(exit_code=code,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'result.json').write_text(json.dumps(info,indent=2));record('antirotation_job_closed',closed_job=dict(name=a.name,machine='local'),config=info,evidence=str(d.relative_to(R)),next='Evaluate actual behavior/geometry and decide next intervention');print(json.dumps(info));raise SystemExit(code)
if __name__=='__main__':main()
