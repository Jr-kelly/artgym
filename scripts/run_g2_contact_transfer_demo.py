"""Existing continuous G2 runtime with final-command clearance projection.
Standalone wrapper retains the old frozen entry untouched. No truth feedback.
"""
import argparse,json,sys
from pathlib import Path
from isaacgym import gymapi # Isaac Gym must precede torch.
import torch,numpy as np
import scripts.run_g2_robust_demo as runtime
from scripts.g2_r800_policy import G2R800Policy
from scripts.wuji_target_clearance_guard import ThumbTargetClearanceGuard as ReducedGuard
from scripts.wuji_target_clearance_guard_v1 import ThumbTargetClearanceGuard as FullGuard

def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--clearance-guard-version',choices=['full-v1','reduced-dev'],default='full-v1');p.add_argument('--target-clearance-spec',type=Path,required=True);a,remaining=p.parse_known_args();sys.argv=[sys.argv[0]]+remaining;out=Path(remaining[remaining.index('--output')+1]);guards=[]
 class GuardedPolicy(G2R800Policy):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs);self.target_guard=(FullGuard if a.clearance_guard_version=='full-v1' else ReducedGuard)(a.target_clearance_spec);guards.append(self.target_guard)
  def command(self,q,goal,**kw):
   previous=self.known.issued[0].cpu().numpy().copy();target,action=super().command(q,goal,**kw);clock=kw.get('clock_s',0)
   if clock is not None and clock>=16:
    safe=self.target_guard.project(previous,target,clock);delta=safe-target
    anchor=self.known.initial if self.known.support_anchor is None else self.known.support_anchor
    self.known.issued=self.tensor(safe);action=((self.known.issued-anchor)/self.known.support_span)[0].cpu().numpy();action[16:]=(safe[16:]-previous[16:])/.025;self.known.last_executed_action=self.tensor(action);self.last_action=action.copy()
    if self.pressure_adapter is not None and not kw.get('issued_target_hold',False):self.pressure_adapter.model.offset[0]+=torch.as_tensor(delta[16:],dtype=torch.float32)
    target=safe.astype(np.float32)
   return target,action
 runtime.G2R800Policy=GuardedPolicy
 try:runtime.main()
 finally:
  if guards and out.exists():(out/'target-clearance-guard.json').write_text(json.dumps(dict(source='estimated_geometry_final_issued_projection',rows=guards[0].rows,actor_unchanged=True,truth_inputs=False,scope='Exact conservative offline mesh check each final command. CPU timing reported; hardware30Hz feasibility still needs actual deployment profiling.'),indent=2))
if __name__=='__main__':main()
