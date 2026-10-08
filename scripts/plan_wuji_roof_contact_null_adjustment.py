"""Diagnostic: can thumb redundancy leave endstop while retaining a roof patch?"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.wuji_measured_hold_reference import _thumb_geometry,_thumb_frame
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--frame',type=int,required=True);p.add_argument('--env',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 z=np.load(a.source/'actual-regrasp-traces.npz');q=z['dof'][a.frame,a.env,:27,0].astype(float);o=z['object'][a.frame,a.env];slider=float(z['dof'][a.frame,a.env,27,0]);f=FunctionalEntryAffordance();O=transform(o[:3],o[3:7]);X=np.linalg.inv(O)@f.kin.forward(q[:7]);g,chain=_thumb_geometry();verts=f.vertices
 def foot(v):
  h=q[7:].copy();h[16:]=v;P=X@_thumb_frame(h,chain);vtx=verts@P[:3,:3].T+P[:3,3];w=np.exp(-(vtx[:,1]-vtx[:,1].min())/.0002);return w@vtx/w.sum()
 record('roof_contact_null_adjustment_feasibility_started',[str(a.source)],dict(frame=a.frame,env=a.env,question='Can thumb leave lowerlimit via redundancy while retaining actual operatingroof pressurefoot and existingotherdigits? Yes: one coordinated shortphysicaladjustment; no: changebearing/grasp rather than pressure gains.'),next_step='Readonlycontinuousnullspacegeometry; no physicalcapacity')
 initial=foot(q[23:]);seed=q[23:].copy();rows=[]
 for target3 in np.linspace(seed[2],.62,37):
  def residual(v):return np.r_[(foot(v)-initial)*1000,(v[2]-target3)*4,(v-seed)*.0001]
  fit=least_squares(residual,np.clip(seed,g.w.lower[16:]+1e-6,g.w.upper[16:]-1e-6),bounds=(g.w.lower[16:]+1e-6,g.w.upper[16:]-1e-6),max_nfev=100,diff_step=1e-5);seed=fit.x;qnext=q.copy();qnext[23:]=seed;H=f.H.inspect(qnext[7:]);af=f.assess(qnext,O,slider,False);rows.append(dict(target_joint3=float(target3),thumb=seed.tolist(),foot_m=foot(seed).tolist(),foot_error_m=float(np.linalg.norm(foot(seed)-initial)),joint3_error_rad=abs(float(seed[2]-target3)),Hbad=H,tail_distance_m=af['tail_roof_distance_m']))
  if rows[-1]['foot_error_m']>.0005 or rows[-1]['joint3_error_rad']>.05 or H:break
 completed=bool(len(rows)==37 and rows[-1]['foot_error_m']<.0005 and not rows[-1]['Hbad']);final=q.copy();final[23:]=seed;result=dict(source=str(a.source),env=a.env,frame=a.frame,initial_foot_m=initial.tolist(),rows=rows,geometry_completed=completed,final_affordance=f.assess(final,O,slider) if completed else None,scope=__doc__+' Read-onlyplanning, fixedactualwrist/otherdigits and observedknife; contactroll not physicalcapacity.')
 (a.output/'result.json').write_text(json.dumps(result,indent=2));(a.output/'planner.py').write_text(Path(__file__).read_text());record('roof_contact_null_adjustment_feasibility_terminal',[str(a.output/'result.json')],dict(geometry_completed=completed,rows=len(rows),last=rows[-1],final_affordance=result['final_affordance']),next_step='Physicalnulladjustment only iforiginalB workspace/geometry improves; otherwise changebearing/grasp');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
