"""Run a finite declared useful comparison; no filler or robot connections."""
import argparse,json,os,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--archive-sha256',required=True)
    p.add_argument('--runtime',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];os.chdir(root)
    env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(a.runtime/'lib'),
        PYTHONPATH=str(root)+':'+str(root/'rl_games'),PYTHONNOUSERSITE='1',
        OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    jobs=[]
    for row in json.loads(a.manifest.read_text()):
        log=(root/'runs/wrap-force-20261004/launchers'/(row['name']+'.log')).open('w')
        cmd=[str(a.runtime/'bin/python'),'-m','scripts.run_wuji_wrap_remote_job',
             '--name',row['name'],'--gpu',str(row['gpu']),'--runtime',str(a.runtime),
             '--source-archive-sha256',a.archive_sha256,'--']+row['command']
        child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        jobs.append((row['name'],child,log));print(row['name'],child.pid,flush=True)
    failures=0
    for name,child,log in jobs:
        code=child.wait();log.close();print(name,code,flush=True);failures+=code!=0
    raise SystemExit(bool(failures))

if __name__=='__main__':main()
