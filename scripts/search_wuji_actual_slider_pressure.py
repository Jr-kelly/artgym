"""One finite useful batch: real recorded loaded contact, physical slider travel score."""
from scripts.wuji_table_transfer_learning_env import TableTransferLearning
import numpy as np,torch,json
from pathlib import Path
from scripts.record_wuji_flat_table_event import record
p=Path('runs/flat-table-20261006/learning/actual-slider-pressure-search-20261006');p.mkdir()
record('actual_slider_loaded_coordination_search_started',[str(p)],dict(uncertainty='Coordinated thumb/support finite motor loads create useful real slidertravel beyond bound-limited pointfeedback?',decision='Materialtravel>5mm -> one native candidate; none -> stop this finite batch.',episodes=32,duration_s=6,no_seed_scan=True),updates=dict(active_jobs=['actual-slider-pressure-search']),next_step='Physicaltravel selects candidate, no proxycontactsuccess.')
e=TableTransferLearning(n=32,seed=61066,data='runs/flat-table-20261006/learning/actual-slider-pressure-search-data');rng=np.random.default_rng(61066);ids=np.r_[np.arange(7,15),np.arange(23,27)];params=rng.normal(0,.28,(32,12));params[0]=0;params[:,8]-=.25;trace=[]
try:
 for i in range(180):
  u=np.clip(i/60,0,1);u=u*u*(3-2*u);motor=e.path[i].expand(e.n,-1).clone();motor[:,ids]+=e.tensor(params)*float(u);e.servo(motor);trace.append(dict(object=e.rb[:,e.object_index].cpu().numpy().copy(),target=e.command_target.cpu().numpy().copy(),q=e.dof[:,:,0].cpu().numpy().copy()))
 obj=e.rb[:,e.object_index];valid=(obj[:,2]>.75)&(obj[:,2]<.80);travel=e.dof[:,27,0]-float(np.load(e.data/'takeover.npz')['slider_q']);score=torch.where(valid,travel,torch.full_like(travel,-1));ix=int(score.argmax());best=float(score[ix]);result=dict(best_travel_m=best,index=ix,parameters=params[ix].tolist(),scope='Development native32episode search; independent native candidate required, table supported.')
 (p/'result.json').write_text(json.dumps(result,indent=2));np.savez_compressed(p/'best-rollout.npz',**{k:np.array([r[k][ix] for r in trace]) for k in trace[0]});print(json.dumps(result),flush=True)
 record('actual_slider_loaded_coordination_search_finished',[str(p/'result.json'),str(p/'best-rollout.npz')],result,updates=dict(active_jobs=[]),next_step='Nativecandidate if>5mm, otherwise stop this batch; no seed scan.')
finally:e.close()
