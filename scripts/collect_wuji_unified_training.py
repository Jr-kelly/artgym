"""Collect responsible-expert complete episodes from the frozen training split."""
import argparse,subprocess,sys,json,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,choices=[2,5],required=True);a=p.parse_args()
 out=R/'runs/unified-policy-20260930'/f'train-data-t{a.seconds}';out.mkdir(parents=True,exist_ok=False);results=[]
 for source in range(4):
  expert='historical' if source<3 else 'source3';checkpoint=f'runs/unified-policy-20260930/experts/{expert}.pth';states=f'research/unified-policy-20260930/data/train-source{source}.npy';dest=out/f'source{source}'
  cmd=[sys.executable,'-m','scripts.collect_wuji_unified','--checkpoint',checkpoint,'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',states,'--span','.04','--output',str(dest),'--seed','2026093030','--stage-seconds',str(a.seconds)]
  with (out/f'source{source}.log').open('w') as f:subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=900,check=True)
  report=json.loads((dest/'report.json').read_text());results.append(dict(source=source,expert=expert,checkpoint_sha256=report['checkpoint_sha256'],states_sha256=report['initial_states_sha256'],sequences_sha256=hashlib.sha256((dest/'sequences.npz').read_bytes()).hexdigest(),report=report));(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 (out/'completed.json').write_text(json.dumps(dict(status='completed',time=time.time(),physics_episodes=512,control_transitions=512*600))+'\n')
if __name__=='__main__':main()
