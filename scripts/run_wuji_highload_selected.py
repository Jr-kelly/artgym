"""Run preserved V13, endpoint-capable highload candidate, or known-load evidence.

Simulation only. Highload candidate retains original criterion failures. The
capacity preset is a complete-task test, not a measurement of original axial B.
Initial geometry adaptation is common across cases, never selected by asset ID.
"""
import argparse,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['baseline','highload','capacity'],default='highload');p.add_argument('--output',type=Path,required=True);p.add_argument('--no-video',action='store_true');a,other=p.parse_known_args()
 selection={'baseline':'research/traction-20261005/FROZEN-CANDIDATE-V13.json','highload':'research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json','capacity':'research/highload-20261005/FROZEN-CAPACITY-CANDIDATE.json'}[a.mode]
 cmd=[sys.executable,'-m','scripts.run_wuji_wrap_selected','--selection',selection,'--output',str(a.output)]
 if a.no_video:cmd.append('--no-video')
 subprocess.run(cmd+other,cwd=R,check=True)
if __name__=='__main__':main()
