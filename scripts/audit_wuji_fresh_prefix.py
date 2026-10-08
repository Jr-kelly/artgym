"""Audit real physics prefix used for learning; no fulltask acceptance."""
import argparse,json
from pathlib import Path
import isaacgym
import torch,numpy as np
from scripts.wuji_fresh_prefix_learning import FreshPrefixRegrasp
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=32);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 root=Path('runs/flat-table-20261006/direct');cfg=dict(source=str(root/'recorded/current-C560-no-extra-load-flip-v565-6p1'),reference=str(root/'preparation/fresh-physical-regrasp-guide-v801/reference.json'),prefix_trace=str(root/'development/current-C560-fresh-no-extra-ring-v743/simulation/trace.npz'),prefix_spec=str(root/'preparation/current-C560-fresh-no-extra-ring-v743/prefix.json'),n=a.envs)
 (a.output/'config.json').write_text(json.dumps(cfg,indent=2));record('fresh_prefix_learning_audit_started',[str(a.output)],cfg,updates={'add_active_jobs':[str(a.output)]},next_step='Verify actualtableprefix carries before any PPO update')
 e=None
 try:
  torch.set_num_threads(1);e=FreshPrefixRegrasp(**cfg);rows=[]
  for repeat in range(3):
   if repeat:e.reset(torch.arange(e.n,device=e.device))
   np.savez_compressed(a.output/('prefix_%d.npz'%repeat),q_1hz=e.prefix_actual_q_1hz.cpu().numpy(),object_1hz=e.prefix_actual_object_1hz.cpu().numpy(),final_q=e.prefix_final_q.cpu().numpy(),final_object=e.prefix_final_object.cpu().numpy())
   row=dict(repeat=repeat,invalid=int(e.failed.sum()),min_prefix_clearance_m=float(e.prefix_min_clearance.min()),min_end_clearance_m=float(e.whole_clearance().min()),max_end_linear_velocity_m_s=float(e.rb[:,e.object_index,7:10].norm(dim=-1).max()),observation_shape=list(e.observation().shape),end_cap_distance_min_m=float(e.cap_distance().min()),end_cap_distance_max_m=float(e.cap_distance().max()));rows.append(row);print(json.dumps(row),flush=True)
  (a.output/'audit.json').write_text(json.dumps({'rows':rows,'scope':__doc__,'eligible_for_training':all(r['invalid']==0 for r in rows)},indent=2))
 finally:
  if e:e.close()
  record('fresh_prefix_learning_audit_terminal',[str(a.output)],updates={'remove_active_jobs':[str(a.output)]},next_step='Read prefix actualcarry audit; valid -> useful PPO; invalid -> fix physical initialization/replay source before learning')
if __name__=='__main__':main()
