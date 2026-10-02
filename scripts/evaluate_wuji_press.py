"""One20s rollout, legal press adapter, K20 and inherited strictS5 scoring."""
import argparse,json,sys,hashlib
from pathlib import Path
from scripts import evaluate_wuji_recovery as evaluator
import numpy as np
from scripts.wuji_press_adapter import install
from scripts.wuji_timed_command_metrics import score_timed_trace

def main():
 p=argparse.ArgumentParser();p.add_argument('--states',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--model',choices=['student','teacher'],default='student');p.add_argument('--press-mm',type=float,default=0);p.add_argument('--resistance-n',type=float,default=0);p.add_argument('--profile',choices=['constant','variable'],default='constant');p.add_argument('--profile-seed',type=int,default=2026100233);p.add_argument('--video',action='store_true');p.add_argument('--disable-press-path',action='store_true');a=p.parse_args();assert not a.disable_press_path or (a.press_mm==0 and a.resistance_n==0)
 states=np.load(a.states);factory=evaluator.make_player;capture={}
 def make_player(cfg,checkpoint):
  cfg.task.env.trainingStates=a.states
  env,player=factory(cfg,checkpoint);configure=env.configure_fixed_grasp_consecutive_evaluation
  def configured(*args,**kwargs):
   answer=configure(*args,**kwargs);install(env,states,a.press_mm,a.resistance_n,a.profile,a.profile_seed,a.disable_press_path);return answer
  env.configure_fixed_grasp_consecutive_evaluation=configured;capture['env']=env;return env,player
 evaluator.make_player=make_player;argv=sys.argv
 try:
  sys.argv=[argv[0],'--checkpoint','runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth','--task','wuji_geometry','--hand','wuji_paper_official_actuator','--object','knife_wuji_real_press_20261002','--geometry-round','real-knife-press-resistance-20261002','--initial-states',a.states,'--output',str(a.output),'--seed','2026100234','--stage-seconds','5','--protocol','S']
  if a.model=='student':sys.argv+=['--unified-student','runs/width-student-distillation-20261002/C1-window1-h200-17314/step_054400.pth']
  if a.video:sys.argv+=['--video','--video-columns','2']
  evaluator.main();env=capture['env'];trace=dict(np.load(a.output/'trace.npz'));diagnostics={k:np.stack([r[k] for r in env.press_diagnostics]) for k in env.press_diagnostics[0]};assert len(diagnostics['thumb_contact'])==len(trace['active']);np.savez_compressed(a.output/'diagnostics.npz',**diagnostics)
  s5=score_timed_trace(trace,150,9,600);short=score_timed_trace(trace,150,3,600);rows=[]
  sourcefile=Path(a.states).with_name('selection.json');sources=json.loads(sourcefile.read_text())['source_order'] if sourcefile.exists() else list(range(len(states)))
  for i,(s,k) in enumerate(zip(s5['records'],short['records'])):
   active=trace['active'][:,i].astype(bool);valid=active & ~trace['fall'][:,i].astype(bool)&~trace['invalid'][:,i].astype(bool);body=len(active)==600 and bool(valid.all()) and bool((trace['drift'][:,i]<.01).all()) and bool((trace['rotation'][:,i]<.25).all());stages=k['stages_attained'];ordered=any(stages[o] and stages[c] for o in [0,2] for c in [1,3] if c>o)
   rows.append(dict(source=int(sources[i]),row=i,K20=bool(ordered and body),S5=bool(s['stable_full_all_endpoints']),ordered_open_close=bool(ordered),body_stable=bool(body),max_drift_m=s['max_drift_m'],max_rotation_rad=s['max_rotation_rad'],endpoint_error_mm=float(np.abs(trace['slider'][-1,i]-trace['goal'][-1,i])*1000),normal_proxy_mean_N=float(diagnostics['normal_net_force_proxy_N'][active,i].mean()),normal_proxy_p95_N=float(np.quantile(diagnostics['normal_net_force_proxy_N'][active,i],.95)),contact_fraction=float(diagnostics['thumb_contact'][active,i].mean()),axial_relative_speed_mean_mps=float(np.abs(diagnostics['relative_axis_velocity_mps'][active,i]).mean()),pd_saturation_proxy=float(diagnostics['pd_saturation_proxy'][active,i].mean()),force_mean_abs_N=float(np.abs(diagnostics['resistance_force_N'][active,i]).mean())))
  report=dict(model=a.model,states_sha256=hashlib.sha256(Path(a.states).read_bytes()).hexdigest(),press=env.press_metadata,positive_power_at_application_max_W=env.press_positive_power_max,controller_memory_error_rad=env.press_memory_error,original_controller_check_rad=getattr(env,'known_controller_max_error',None),K20=sum(r['K20'] for r in rows),S5=sum(r['S5'] for r in rows),n=len(rows),records=rows,scope='Simulation of approximated measured body; no physical force calibration. Passive joint effort has articulation reaction; no slider drive, force only opposes measured relative velocity. Smooth law does not model static detents.')
  assert env.press_positive_power_max<=1e-8
  (a.output/'press-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['model','K20','S5','n','positive_power_at_application_max_W','original_controller_check_rad']}))
 finally:evaluator.make_player=factory;sys.argv=argv
if __name__=='__main__':main()
