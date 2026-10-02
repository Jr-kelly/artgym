"""Fetch only completed immutable runs and independently rescore raw episodes."""
import argparse,json,os,shlex,subprocess,sys
from pathlib import Path
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_contract import sha
from scripts.wuji_width_jobs import host_tool_environment

def collect(queues,manifest,output):
    tasks=[]
    for path in queues:
        q=json.loads(Path(path).read_text())
        assert q['historical_final_access'] is False
        assert all(t['status']=='complete' for t in q['tasks'])
        tasks+=q['tasks']
    ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
    paths=[t['output'] for t in tasks if not (R/t['output']/'geometry-receipt.json').exists()]
    record('completed_queue_raw_fetch_started',evidence=str(manifest.relative_to(R)),tasks=len(tasks),missing_local=len(paths),next='Read only completed samebackend outputs; no new policy runs')
    if paths:
        subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*['wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/./'+p for p in paths],str(R)+'/'],check=True,timeout=300,env=host_tool_environment())
    teacher=json.loads((D/'STATE.json').read_text())['models']['runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth']
    m=dict(teacher_sha256=teacher,historical_final_access=False,runs=[])
    for t in tasks:
        m['runs'].append(dict(directory=t['output'],selection=t['selection'],role=t['role'],geometry=t['geometry'],protocol=t['identity']['protocol'],model_sha256=t['identity']['model_sha256'],states_sha256=t['identity']['states_sha256'],selection_sha256=t['identity']['selection_sha256'],trace_sha256=sha(R/t['output']/'trace.npz')))
    assert not manifest.exists();manifest.write_text(json.dumps(m,indent=2)+'\n')
    e=os.environ.copy();e.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH='.:rl_games',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',CUDA_VISIBLE_DEVICES='')
    subprocess.run(['/home/agiuser/miniconda3/envs/artgym/bin/python','-m','scripts.analyze_wuji_width','--manifest',str(manifest),'--output',str(output)],cwd=R,env=e,check=True,timeout=300)
    record('completed_queue_raw_independent_rescore_finished',evidence=str(manifest.relative_to(R)),analysis=str(output.relative_to(R)),tasks=len(tasks),next='Use dev/confirmation only for selection; frozen final only for reporting')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--queues',nargs='+',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    collect(a.queues,a.manifest.resolve(),a.output.resolve())
