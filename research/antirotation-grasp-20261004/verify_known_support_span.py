import json
from pathlib import Path
from isaacgym import gymapi
import torch
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_antirotation_goal import record
b=Path('runs/antirotation-grasp-20261004');p=json.loads((b/'pickup-plans-v1/opposed/table-support-projected-motor-plan-v6-retry1.json').read_text());g=DigitGeometry();lo=torch.tensor(g.w.lower,dtype=torch.float32);hi=torch.tensor(g.w.upper,dtype=torch.float32);q=torch.tensor([p['close_q']],dtype=torch.float32)
c=KnownWujiController(lo,hi,1);c.configure_support(.12,.025);ids=torch.tensor([0]);c.reset(ids,q);r=torch.zeros_like(q);r[0,4]=10;reference=q.clone();scale=torch.tensor([.12]*16+[.15]*4);issued=[]
for _ in range(6):
 previous=c.issued.clone();a=bounded_motor_residual_action(reference,c,r,scale);motor=c.step(a);assert (motor[:,:16]-previous[:,:16]).abs().max()<.025002;assert (motor>=lo-1e-7).all() and (motor<=hi+1e-7).all();assert (c.last_executed_action[:,:16]*.12+q[:,:16]-motor[:,:16]).abs().max()<2e-6;issued.append(float(motor[0,4]-q[0,4]))
assert issued[-1]>.11999,issued
c.reset(ids,q);assert not c.last_executed_action.any()
result={'scope':'Actual original URDF limits and newknowncommand conversion check; no physics/contact success claim','support_span_rad':.12,'support_step_rad':.025,'issued_indexed_support_offsets_rad':issued,'limit_rate_and_actual_history_checks_passed':True,'reset_action_memory_cleared':True}
out=b/'controller-compatibility-v1/known-span.json';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_text(json.dumps(result,indent=2));print(json.dumps(result));record('opt_in_support_span_command_check_passed',evidence=str(out),config=result,next='Actual continuous scene parity/behavior and meaningful randomized training after complete reference passes')
