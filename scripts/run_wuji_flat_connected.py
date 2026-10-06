"""Full-flat physical front to existing B; nominal and small representative checks."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
from scripts.record_wuji_flat_table_event import record
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=['nominal','placement-error','placement-error-opposite','load125','mid-geometry'],default='nominal');p.add_argument('--no-video',action='store_true');a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
 c=json.load(open(ROOT/'runs/flat-table-20261006/development/continuous-existing-B-v1-20261006/command.json'));c[0]=sys.executable;c[c.index('--output')+1]=str(a.output/'simulation')
 if a.no_video:c.remove('--video')
 prefix=json.load(open(ROOT/c[c.index('--flat-table-prefix')+1]));changes={}
 if a.case.startswith('placement-error'):
  sign=1 if a.case=='placement-error' else -1;prefix['physical_initial_xy']=[.37+sign*.001,-.5695+sign*.001];prefix['physical_initial_yaw_deg']=45+sign*.5;c+=['--pose-estimate-bias-m',str(sign*.001)];changes=dict(initial_xy_offset_m=[sign*.001,sign*.001],initial_yaw_offset_deg=sign*.5,postplacement_estimate_bias_x_m=sign*.001,controller='Same motor prefix and B; no percase tuning')
 elif a.case=='load125':c[c.index('--newknife-resistance')+1]='runs/singlepush-20261005/configs/resistance-1.25.json';changes=dict(resistance_capacity_N=1.25,controller='Unchanged nominal A and B')
 elif a.case=='mid-geometry':
  old=json.load(open(ROOT/'runs/contact-transfer-20261006/frozen/mid-high-delay/physical-v1/command.json'))
  for flag in ['--grasp-plan','--table-calibration','--acquisition-path','--thumb-reference-override','--postlift-regrasp','--knife-asset','--newknife-resistance']:c[c.index(flag)+1]=old[old.index(flag)+1]
  c+=['--actuation-delay-frames','1','--observation-noise','.001','--observation-bias','.0005'];changes=dict(geometry='Existing mid-high-delay:145.5x19.3x8.2mm,32.4x7.2x2.1mm slider,56g',resistance_capacity_N=1.25,delay_frames=1,controller='Same A prefix and actor; existing estimate-generated B geometry configuration')
 (a.output/'prefix.json').write_text(json.dumps(prefix));c[c.index('--flat-table-prefix')+1]=str(a.output/'prefix.json');(a.output/'command.json').write_text(json.dumps(c,indent=2));(a.output/'case.json').write_text(json.dumps(dict(case=a.case,changes=changes,simulation_only=True),indent=2));files=[Path('scripts/run_g2_flat_table_demo.py'),Path('scripts/run_wuji_flat_connected.py'),Path('scripts/evaluate_wuji_flat_connected.py'),Path(c[c.index('--residual-checkpoint')+1]),Path(c[c.index('--thumb-reference-override')+1]),Path(c[c.index('--postlift-regrasp')+1]),a.output/'prefix.json'];(a.output/'source-hashes.json').write_text(json.dumps({str(f):hashlib.sha256((ROOT/f if not f.is_absolute() else f).read_bytes()).hexdigest() for f in files},indent=2))
 record('flat_connected_case_started',[str(a.output/'command.json')],dict(case=a.case,uncertainty='Does connected fullflat controller retain actual behavior under this representative changed condition?',decision='Pass preserves necessary local capability; fail identifies specific next adaptation',changes=changes),updates=dict(active_jobs=[a.case]),next_step='Read actual connected result; no seed/repeated success sweep')
 try:
  subprocess.run(c,cwd=ROOT,check=True);subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_flat_connected','--trial',str(a.output/'simulation')],cwd=ROOT,check=True)
  result=json.load(open(a.output/'simulation/connected-evaluation.json'));record('flat_connected_case_finished',[str(a.output/'simulation/connected-evaluation.json')],dict(case=a.case,result=result),updates=dict(active_jobs=[]),next_step='Use physical outcome to select remaining necessary local check')
 except Exception as e:
  record('flat_connected_case_failed',[str(a.output/'command.json')],dict(case=a.case,error=str(e)),updates=dict(active_jobs=[]),next_step='Diagnose first actual divergence, no unchanged retry');raise
if __name__=='__main__':main()
