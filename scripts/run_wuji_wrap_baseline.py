"""One actual baseline with new synchronized contact distribution; preserved actor and task."""
import argparse,json,sys,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=['nominal','higher-load-failure','thin-failure'],default='nominal');p.add_argument('--test-load',type=float,default=0.);p.add_argument('--serial-cell',type=Path);p.add_argument('--no-video',action='store_true');a=p.parse_args()
 x=json.loads(Path('research/antirotation-grasp-20261004/DEMO-COMMANDS.json').read_text());cmd=x['cases'][a.case]['command'];cmd[0]=sys.executable;cmd[cmd.index('--output')+1]=str(a.output);cmd+=['--wrap-contact-measurement'];
 if a.no_video:cmd.remove('--video')
 if a.test_load:cmd+=['--opposing-axial-test-load',str(a.test_load)]
 if a.serial_cell:cmd+=['--knife-asset',str(a.serial_cell),'--physics-hz','960','--serial-load-cell-diagnostic']
 subprocess.run(cmd,check=True)
 subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_antirotation','--trial',str(a.output)],check=True)
if __name__=='__main__':main()
