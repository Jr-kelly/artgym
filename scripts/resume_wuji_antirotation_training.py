"""Restore a retained experimental model/Adam/RNG; starts new physical episodes."""
import argparse,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--range',choices=['04','12'],default='04')
    p.add_argument('--candidate',choices=['range04','range12','necessary24-frozen-thumb','necessary24-joint'],help='Explicit retained experiment; new necessary24 defaults to one update25->26')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--updates',type=int,help='Total updates including retained checkpoint; default one material recovery update, never automatic candidate promotion')
    p.add_argument('--show-command',action='store_true');a=p.parse_args()
    candidate=a.candidate or 'range'+a.range
    necessary=candidate.startswith('necessary24-');start=25 if necessary else 50
    if necessary:name='necessary24-retained750-'+candidate[len('necessary24-'):]+'-frozen25-v3'
    else:
        selected=candidate[-2:];name='strict16-table-prior-closure-longhorizon-range'+selected+'-reset750-'+('v8' if selected=='04' else 'v9')
    identity=R/'runs/antirotation-grasp-20261004/jobs'/name/'identity.json'
    cmd=json.loads(identity.read_text())['command'];cmd[0]=sys.executable
    total=a.updates if a.updates is not None else start+1
    assert cmd[1:3]==['-m','scripts.train_wuji_robust_residual'] and total>start
    cmd[cmd.index('--output')+1]=str(a.output.resolve());cmd[cmd.index('--updates')+1]=str(total)
    i=cmd.index('--initialize-model-from');del cmd[i:i+2]
    if '--reset-residual-head' in cmd:cmd.remove('--reset-residual-head')
    checkpoint=Path('runs/antirotation-grasp-20261004/train')/name/('update_%06d.pth'%start);cmd+=['--resume',str(checkpoint)]
    print(json.dumps({'candidate':candidate,'command':cmd,'scope':'Experimental checkpoint recovery only. Model/Adam/CPU-CUDA-NumPy/per-scene RNG restored; new physical episodes, no bitwise solver-state or behavior success claim. Recovery alone never promotes a candidate.'}),flush=True)
    if a.show_command:return
    assert not a.output.exists(),'Choose a new output; retain original evidence'
    assert (R/checkpoint).is_file(),'Extract learning archive at repository root'
    for flag in ['--thumb-reference','--initial-estimate-scene','--training-geometry-schedule','--training-asset-registry']:
        assert (R/cmd[cmd.index(flag)+1]).is_file(),'Extract evidence configuration archive at repository root'
    env=os.environ.copy();env.update(PYTHONPATH=str(R)+':'+str(R/'rl_games'),PYTHONNOUSERSITE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    env['PATH']=str(Path(sys.executable).parent)+':'+env.get('PATH','')
    subprocess.run(cmd,cwd=R,env=env,check=True)
if __name__=='__main__':main()
