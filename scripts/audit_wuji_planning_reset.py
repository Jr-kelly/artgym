"""Repeated identical planning episodes: no training or demo acceptance."""
import argparse,json,time
from pathlib import Path
import isaacgym
import torch,numpy as np
from scripts.wuji_regrasp_learning import RegraspLearning
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--case',type=int,default=787);p.add_argument('--safe-reset-order',action='store_true');p.add_argument('--no-cache-retirement',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
 source='runs/flat-table-20261006/direct/recorded/actual-pressure-settled-v786-4s';ref='runs/flat-table-20261006/direct/preparation/settled-functional-course-v786/reference.json';record('planning_cache_repeated_pause_audit_started',[str(a.output),'scripts/audit_wuji_planning_reset.py'],{'case':a.case,'safe_reset_order':a.safe_reset_order,'repeats':3,'seconds':8,'clear_contact_cache_initialization_only':True},next_step='Measure comparability beforemorecourse search; no nativegoalsuccess claim')
 e=RegraspLearning(32,source,ref,physx_buffer_multiplier=16,clear_contact_cache_on_reset=not a.no_cache_retirement,safe_reset_order=a.safe_reset_order);qs=[];objects=[];results=[];began=time.monotonic()
 try:
  pose=torch.zeros((32,3),device=e.device);pose[16:]=torch.tensor([.0003,-.00015,.0001],device=e.device);joint=torch.zeros((32,27),device=e.device);joint[16:]=torch.tensor([.001 if i%2 else -.001 for i in range(27)],device=e.device);act=torch.zeros((32,28),device=e.device);act[:,27]=-.75
  for i in range(3):
   e.reset(torch.arange(32,device=e.device),perturb=False,physical_offsets=(pose,joint));qhist=[];ohist=[];held=torch.zeros(32,device=e.device)
   for tick in range(240):
    _,_,_,info=e.step(act);held+=info['held'].float();qhist.append(e.dof[:,:27,0].clone());ohist.append(e.rb[:,e.object_index].clone())
   qs.append(torch.stack(qhist).cpu().numpy());objects.append(torch.stack(ohist).cpu().numpy());row={'repeat':i,'held_seconds':(held/30).cpu().numpy().tolist(),'final_error':info['error'].cpu().numpy().tolist(),'elapsed_wall_seconds':time.monotonic()-began};results.append(row);print(json.dumps(row),flush=True)
  np.savez_compressed(a.output/'repeated-planning-traces.npz',q=np.array(qs),object=np.array(objects));out={'results':results,'same_env_max_q_difference_rad':float(max(abs(qs[i]-qs[0]).max() for i in [1,2])),'same_env_max_object_xyz_difference_m':float(max(abs(objects[i][:,:,:3]-objects[0][:,:,:3]).max() for i in [1,2])),'scope':__doc__+' Recorded-sourceplanning only; two contactretirement steps precede eachnew episode, nota fulltablephysicalroute.'};(a.output/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='results'}));record('planning_cache_repeated_pause_audit_terminal',[str(a.output/'result.json'),str(a.output/'repeated-planning-traces.npz')],{k:v for k,v in out.items() if k!='results'},next_step='Use measuredcomparisonvariability forcourse selection; thenfunctionalphysicalarrival+B beforefreshroute')
 finally:e.close()
if __name__=='__main__':main()
