"""Selected-source held diagnostic scenes with per-grasp priors and true issued preparation.

This is not a continuous-pickup training scene. Source identity configures a
known initial motor plan; no grasp/asset ID or simulator truth enters the actor.
"""
import argparse,json
from pathlib import Path
import numpy as np

R=Path(__file__).resolve().parents[1];B=R/'runs/wrap-force-20261004'

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',nargs='+',type=int,choices=[1,2],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[];shifts=np.linspace(0,.04,41)
 for source in a.sources:
  folder=B/'comparison/four-sources-v1'/('source%d'%source)
  if source==1:
   pf=folder/'negative-tangent-prepare-v4/motor-plan.json';rf=pf.parent/'reference.json';cf=folder/'settled-v2/handover-calibration.json';trial=B/'comparison/negative-tangent750-v4/source1'
  else:
   pf=folder/'registered-v3/motor-plan.json';rf=pf.parent/'reference.json';cf=pf.parent/'matched-initial-calibration.json';trial=B/'comparison/registered750-v3/source2'
   if not cf.exists():
    w=np.asarray(json.loads(pf.read_text())['wrist_in_knife']);relative=np.linalg.inv(w);slider=relative.copy();slider[:3,3]+=relative[:3,:3]@np.array([0,.0075,-.02205]);cf.write_text(json.dumps(dict(object_in_wrist=relative.tolist(),slider_in_wrist=slider.tolist()),indent=2)+'\n')
  plan=json.loads(pf.read_text());ref=json.loads(rf.read_text());assert ref['all_feasible'];times=np.array([r['shift_m'] for r in ref['rows']]);q=np.array([r['q_thumb'] for r in ref['rows']]);reference=dict(ref,rows=[dict(shift_m=float(s),q_thumb=[float(np.interp(s,times,q[:,j])) for j in range(4)],feasible=True) for s in shifts],resampling_scope='Common41shift grid retaining full40mm command and complete virtualpath; physicalbatch comparison required beforetraining')
  actual=json.loads((trial/'plan.json').read_text());arm=actual['arm_lift'];target=plan.get('post_lift_close_q',plan['close_q']);way=[]
  if plan.get('post_lift_thumb_motor_waypoints'):
   for r in plan['post_lift_thumb_motor_waypoints']:
    values=list(plan['close_q']);values[16:]=r['q_thumb'];way.append(dict(time_s=r['time_s'],q=values))
  else:way=[dict(time_s=float(t),q=list(plan['close_q'])) for t in np.linspace(12,14,31)]
  rows.append(dict(motor_plan=plan,thumb_reference=reference,support_target_q=target,support_motor_waypoints=way,held_arm_q=arm,calibration=json.loads(cf.read_text()),estimate=dict(source='Fixed offline representative %d initial geometry estimate'%source,uncertainty_m=.001,handle_size_WTL_m=[.016,.012,.135],slider_size_WTL_m=[.01,.003,.03],slider_contact_shift_m=[0,0,0]),selection_source=source))
 scene=dict(scope='Initial noisy estimate guided common motor planning; no runtime object/contact truth or assetID actor input',held_diagnostic=True,plan=rows[0]['motor_plan'],acquisition=dict(approach_q=[rows[0]['held_arm_q']]*2,lift_q=[rows[0]['held_arm_q']]*2),calibration=rows[0]['calibration'],initial_estimated_plans=rows,repeat_initial_estimate_templates=True,nominal_hand_friction=.8,nominal_knife_friction=1.8,template_scope=__doc__,geometry_split=dict(train='000–011',heldout='012–015'),grasp_pool_expanded=False)
 (a.output/'scene.json').write_text(json.dumps(scene,indent=2)+'\n');(a.output/'reference.json').write_text(json.dumps(rows[0]['thumb_reference'],indent=2)+'\n');print(json.dumps(dict(sources=a.sources,held_diagnostic=True)))

if __name__=='__main__':main()
