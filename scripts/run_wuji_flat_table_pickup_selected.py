"""Reproduce native whole-flat pickup v104; B handoff remains incomplete."""
import argparse,json,subprocess,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-video',action='store_true');a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
 c=json.load(open(ROOT/'runs/flat-table-20261006/development/clamped-extraction-v104/command.json'));c[0]=sys.executable;c[c.index('--output')+1]=str(a.output/'simulation')
 if a.no_video:c.remove('--video')
 # Prefix-only terminal keeps last finite motor target; no idealgrasp return at t0.
 (a.output/'command.json').write_text(json.dumps(c,indent=2));files=[Path('scripts/run_g2_flat_table_demo.py'),Path('scripts/run_wuji_flat_table_pickup_selected.py'),Path('scripts/evaluate_wuji_prefix_hold.py'),Path('runs/flat-table-20261006/preparation/clamped-extraction-v104/prefix.json'),Path('runs/newknife-20261005/train/center-tail-constant-motor-v1/update_000100.pth')];(a.output/'source-hashes.json').write_text(json.dumps({str(x):hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in files},indent=2));subprocess.run(c,cwd=ROOT,check=True);subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_prefix_hold','--trial',str(a.output/'simulation'),'--prefix-duration','47','--hold-start','44','--hold-end','47'],cwd=ROOT,check=True)
 result=json.load(open(a.output/'simulation/prefix-hold-evaluation.json'));(a.output/'result.json').write_text(json.dumps(dict(result,initial=dict(x=.37,y=-.5695,yaw_deg=45,whole_flat=True),pose_source='sim_oracle initial and explicit v97/v104 development prior; fixed nominal demonstration',B='not connected',vision_validated=False,real_robot_ran=False),indent=2));assert result['whole_pickup'],'Native wholeknife pickup failed; evidence retained'
if __name__=='__main__':main()
