"""Original complete B in the candidate's unreset fresh physics episode.

No pose/q/velocity setters. This is learning capacity evidence, not independent
native quality/video validation or hardware evidence.
"""
import json,hashlib,shutil
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform
from scripts.wuji_retained_push_skill import RetainedPushSkill
from scripts.record_wuji_flat_table_event import record

def probe(e,chosen,output):
 output=Path(output);output.mkdir(parents=True,exist_ok=False);closed_slider_q=float(e.initial_slider[chosen]);spec=dict(start_s=0.,preparation_seconds=4.,knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json',entry_reference_adaptation='measured-hold',entry_pressure_coordinates='cartesian-normal',task_stroke_m=getattr(e,'task_stroke_m',.03))
 source=Path(__file__);shutil.copyfile(source,output/'executed-capacity-probe-source.py');(output/'executed-source.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'selected_original_closed_slider_q_m':closed_slider_q},indent=2))
 record('fresh_learning_candidate_sameepisode_fullB_started',[str(output)],{'chosen_env':chosen,'representation':'FreshA actualphysics -> policyrealtransfer -> fullB noreset','scope':__doc__},next_step='Measure actualBstroke/held1s andactualhandgeometry; functionalproxy is only trigger')
 skill=RetainedPushSkill(e.cfg,spec,output);motors=e.command_target.clone();states=[];reason=None;minclear=float('inf');run=[]
 try:
  for tick in range(300):
   q=e.dof[chosen,:27,0].cpu().numpy();issued=e.command_target[chosen].cpu().numpy();o=e.rb[chosen,e.object_index].cpu().numpy();slider=float(e.dof[chosen,27,0]);O=transform(o[:3],o[3:7]);arm,hand=skill.command(tick/30,O,q[:7],q[7:],issued[:7],issued[7:],slider);motors[chosen]=e.tensor(np.r_[arm,hand]);e.servo(motors);q=e.dof[chosen,:27,0].cpu().numpy();o=e.rb[chosen,e.object_index].cpu().numpy();slider=float(e.dof[chosen,27,0]);clear=float(e.whole_clearance()[chosen]);minclear=min(minclear,clear);states.append((q,e.command_target[chosen].cpu().numpy(),o,slider,e.dof[chosen,:27,1].cpu().numpy(),float(e.dof[chosen,27,1])));
   if skill.taken:run.append((slider-skill.push_slider_start,clear,slider-closed_slider_q))
   if clear<.002:reason='Lostcarrying in original B';break
 except (RuntimeError,ValueError) as exc:reason=type(exc).__name__+': '+str(exc)
 if states:np.savez_compressed(output/'actual-B-trace.npz',q=np.array([s[0] for s in states]),issued=np.array([s[1] for s in states]),object=np.array([s[2] for s in states]),slider=np.array([s[3] for s in states]),velocity=np.array([s[4] for s in states]),slider_velocity=np.array([s[5] for s in states]))
 deltas=np.array([p[0] for p in run]);hold=0;maxhold=0
 for delta,clear,absolute_extension in run:hold=hold+1 if delta>.02 and absolute_extension>.02 and clear>.002 else 0;maxhold=max(maxhold,hold)
 from scripts.check_wuji_action_quality import HandIntersection
 H=HandIntersection();selfrows=[{'frame':i,'self':H.inspect(s[0][7:])} for i,s in enumerate(states)];self_frames=sum(bool(r['self']) for r in selfrows);(output/'actual-hand-geometry.json').write_text(json.dumps({'rows':selfrows,'self_frames':self_frames,'scope':'Allsaved30Hz actualhandq hull audit, no FKposecomparison/video/hardware'},indent=2))
 result=dict(scope=__doc__,chosen_env=chosen,actual_frames=len(states),fullB_started=skill.taken,fullB_calls=len(run),actual_slider_max_m=float(deltas.max()) if len(deltas) else 0.,actual_slider_last_m=float(deltas[-1]) if len(deltas) else 0.,last1s_min_m=float(deltas[-30:].min()) if len(deltas)>=30 else None,continuous_above20mm_s=maxhold/30,min_whole_clearance_m=minclear if states else None,actual_self_frames=self_frames,failure=reason,actor_sha256='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e');absolute=np.array([p[2] for p in run]);result.update(original_closed_slider_q_m=closed_slider_q,absolute_extension_max_m=float(absolute.max()) if len(absolute) else 0.,absolute_extension_last1s_min_m=float(absolute[-30:].min()) if len(absolute)>=30 else None);result['capacity_pass']=reason is None and maxhold>=30 and result['last1s_min_m']>.02 and result['absolute_extension_last1s_min_m']>.02 and self_frames==0;progress=max(0,min(result['actual_slider_max_m'],result['absolute_extension_max_m'],.02)/.02);result['reward']=20. if result['capacity_pass'] else 5.*progress-float(getattr(e,'failure_penalty',60.))-(5. if self_frames else 0.);(output/'result.json').write_text(json.dumps(result,indent=2));record('fresh_learning_candidate_sameepisode_fullB_terminal',[str(output/'result.json'),str(output/'actual-B-trace.npz')],result,next_step='Capacitypass -> independentnative samepolicy/noise livefullB; fail -> retain evidence andlearn actualcapacity');print(json.dumps(result),flush=True);return result
