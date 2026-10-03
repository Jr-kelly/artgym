"""Detached useful remote experiment worker; persistent identity and exit evidence."""
import argparse,subprocess,os,json,datetime
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();j=json.loads(a.manifest.read_text());R=Path(j['root']);d=R/j['job_dir'];d.mkdir(parents=True,exist_ok=False);env=os.environ.copy();env.update(j['environment']);j.update(launcher_pid=os.getpid(),start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with (d/'output.log').open('w') as f:
  child=subprocess.Popen(j['command'],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT);j['child_pid']=child.pid;(d/'identity.json').write_text(json.dumps(j,indent=2));code=child.wait()
 j.update(exit_code=code,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(d/'result.json').write_text(json.dumps(j,indent=2));raise SystemExit(code)
if __name__=='__main__':main()
