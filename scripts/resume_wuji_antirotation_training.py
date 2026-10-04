"""Restore a retained experimental model/Adam/RNG; starts new physical episodes."""
import argparse,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--range',choices=['04','12'],default='04')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--updates',type=int,default=51,help='Total updates including retained50; original candidates were negative and are not promoted by recovery')
    p.add_argument('--show-command',action='store_true');a=p.parse_args()
    name='strict16-table-prior-closure-longhorizon-range'+a.range+'-reset750-'+('v8' if a.range=='04' else 'v9')
    identity=R/'runs/antirotation-grasp-20261004/jobs'/name/'identity.json'
    cmd=json.loads(identity.read_text())['command'];cmd[0]=sys.executable
    assert cmd[1:3]==['-m','scripts.train_wuji_robust_residual'] and a.updates>50
    cmd[cmd.index('--output')+1]=str(a.output.resolve());cmd[cmd.index('--updates')+1]=str(a.updates)
    i=cmd.index('--initialize-model-from');del cmd[i:i+2];cmd.remove('--reset-residual-head')
    checkpoint=Path('runs/antirotation-grasp-20261004/train')/name/'update_000050.pth';cmd+=['--resume',str(checkpoint)]
    print(json.dumps({'command':cmd,'scope':'Experimental negative50 candidate. Model/Adam/CPU-CUDA-NumPy/per-scene RNG restored; new physical episodes, no bitwise solver-state or behavior success claim.'}),flush=True)
    if a.show_command:return
    assert not a.output.exists(),'Choose a new output; retain original evidence'
    assert (R/checkpoint).is_file(),'Extract learning archive at repository root'
    for flag in ['--thumb-reference','--initial-estimate-scene','--training-geometry-schedule','--training-asset-registry']:
        assert (R/cmd[cmd.index(flag)+1]).is_file(),'Extract evidence configuration archive at repository root'
    env=os.environ.copy();env.update(PYTHONPATH=str(R)+':'+str(R/'rl_games'),PYTHONNOUSERSITE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    env['PATH']=str(Path(sys.executable).parent)+':'+env.get('PATH','')
    subprocess.run(cmd,cwd=R,env=env,check=True)
if __name__=='__main__':main()
