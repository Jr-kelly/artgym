"""One entry for retained continuous simulation examples and honest failures."""
import argparse,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    data=json.loads((R/'research/antirotation-grasp-20261004/DEMO-COMMANDS.json').read_text());p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',choices=sorted(data['cases']),default='nominal');p.add_argument('--output',type=Path,required=True);p.add_argument('--show-command',action='store_true');a=p.parse_args();row=data['cases'][a.case];cmd=list(row['command']);assert cmd[1:3]==['-m','scripts.run_g2_robust_demo'];cmd[0]=sys.executable;cmd[cmd.index('--output')+1]=str(a.output.resolve());print(json.dumps(dict(case=a.case,role=row['scientific_role'],recorded_functional_pass=row['original_functional_pass'],command=cmd),ensure_ascii=False),flush=True)
    if a.show_command:return
    assert not a.output.exists(),'Select a new output; preserve previous experiments'
    for name in row['config_dependencies']:assert (R/name).is_file(),'Extract evidence configuration archive at repository root: '+name
    env=os.environ.copy();env.update(PYTHONPATH=str(R)+':'+str(R/'rl_games')+(':'+env['PYTHONPATH'] if env.get('PYTHONPATH') else ''),PYTHONNOUSERSITE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4');env['PATH']=str(Path(sys.executable).parent)+':'+env.get('PATH','');subprocess.run(cmd,cwd=R,env=env,check=True);subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_antirotation','--trial',str(a.output.resolve())],cwd=R,env=env,check=True)
if __name__=='__main__':main()
