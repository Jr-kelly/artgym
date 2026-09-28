"""Wait for a bounded job to terminate, then launch a recorded sequential job."""
import argparse,json,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--after',required=True);p.add_argument('--wait-seconds',type=int,default=5400);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();start=time.monotonic()
 while time.monotonic()-start<a.wait_seconds:
  f=R/'runs/multigrasp-20260928'/a.after/'status.json'
  if f.exists() and json.loads(f.read_text()).get('status') in ['completed','failed']:break
  time.sleep(10)
 else:raise TimeoutError('Predecessor not terminal')
 cmd=a.command[1:] if a.command[0]=='--' else a.command
 cmd=[sys.executable if x=='PYTHON' else x for x in cmd]
 subprocess.run(cmd,cwd=R,check=True)
if __name__=='__main__':main()
