"""Own exactly one experiment process; record exit, terminate it at its deadline."""
import argparse,json,os,signal,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--timeout',type=float,required=True);a=p.parse_args()
    r=json.loads(a.record.read_text());started=time.time();deadline=started+a.timeout
    if r.get('deadline_utc'):deadline=min(deadline,datetime.fromisoformat(r['deadline_utc']).timestamp())
    child=subprocess.Popen(r['command'],cwd=r['pin'],start_new_session=True)
    r.update(pid=child.pid,supervisor_pid=os.getpid(),process_start_ticks=Path('/proc',str(child.pid),'stat').read_text().split(') ')[1].split()[19])
    a.record.write_text(json.dumps(r,indent=2)+'\n');timed_out=False
    while child.poll() is None:
        if time.time()>=deadline:
            timed_out=True;os.killpg(child.pid,signal.SIGINT)
            try:child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            break
        time.sleep(2)
    r.update(exit_code=child.returncode,timed_out=timed_out,elapsed_seconds=time.time()-started,ended_utc=datetime.now(timezone.utc).isoformat())
    a.record.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
