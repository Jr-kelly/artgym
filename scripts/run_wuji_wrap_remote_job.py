"""Portable remote experiment receipt, synchronized into the primary journal by SSH.

Runs the supplied useful experiment once; never generates utilization filler.
"""
import argparse,datetime,hashlib,json,os,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--source-archive-sha256',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();R=Path(__file__).resolve().parents[1];d=R/'runs/wrap-force-20261004/jobs'/a.name;d.mkdir(parents=True,exist_ok=False);cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command
 env=os.environ.copy();env.update(PATH=str(a.runtime/'bin')+':/usr/bin:/bin',LD_LIBRARY_PATH=str(a.runtime/'lib'),PYTHONPATH=str(R)+':'+str(R/'rl_games'),PYTHONNOUSERSITE='1',CUDA_VISIBLE_DEVICES=str(a.gpu),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',MAX_JOBS='2',TORCH_EXTENSIONS_DIR='/tmp/wuji-wrap-torch-extensions',PYTHONUNBUFFERED='1')
 hashes={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (R/'scripts').glob('*.py')}
 info=dict(command=cmd,machine='authorized-development-10.13.160.5:33024',gpu=a.gpu,launcher_pid=os.getpid(),source_archive_sha256=a.source_archive_sha256,source_sha256=hashes,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 journal=R/'research/wrap-force-20261004/events-remote.jsonl';journal.parent.mkdir(parents=True,exist_ok=True)
 def write(event):
  row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,job=info)
  with journal.open('a') as f:f.write(json.dumps(row)+'\n')
  (R/'WUJI_GOAL_HANDOFF.md').write_text('# Remote wrap-force experiment receipt\n\nPrimary handoff/journal is on the local experiment clone. No real robot commands.\n\n'+json.dumps(row,indent=2)+'\n')
 with (d/'output.log').open('w') as log:
  child=subprocess.Popen(cmd,env=env,cwd=R,stdout=log,stderr=subprocess.STDOUT);info['pid']=child.pid;(d/'identity.json').write_text(json.dumps(info,indent=2)+'\n');write('remote_job_started');code=child.wait()
 info.update(exit_code=code,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'result.json').write_text(json.dumps(info,indent=2)+'\n');write('remote_job_closed');raise SystemExit(code)

if __name__=='__main__':main()
