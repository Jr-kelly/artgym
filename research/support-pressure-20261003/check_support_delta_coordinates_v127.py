"""Legal FK coordinate and inherited-policy preservation contract, no physics."""
import isaacgym
import torch,json,numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_support_delta_coordinates import SupportDeltaCoordinates
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action
from scripts.wuji_robust_learning import ResidualActorCritic
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_support_goal import R,D,record
B=R/'runs/support-pressure-20261003';saved=torch.load(B/'train/joint-noisier-continuation-v31/update_000750.pth',map_location='cpu');model=ResidualActorCritic();model.load_state_dict(saved['model']);reference={k:v.clone() for k,v in model.actor.state_dict().items()};q=torch.tensor(json.loads((B/'staged-brace-config-v86/nominal/support.json').read_text())['post_lift_target_q'],dtype=torch.float32)[None];h=WujiKinematics();known=KnownWujiController(torch.tensor(h.lower,dtype=torch.float32),torch.tensor(h.upper,dtype=torch.float32),1);known.reset(torch.tensor([0]),q)
rotation=np.asarray(json.loads((R/'research/robust-knife-family-20261003/handover-from-v25-v1.json').read_text())['object_in_wrist'])[:3,:3];quat=torch.tensor(Rotation.from_matrix(rotation).as_quat(),dtype=torch.float32)[None];scale=torch.tensor(saved['action_scale']);public=torch.randn(1,154);original=model.actor_logits(public)
with torch.no_grad():model.actor[-1].weight[:16].zero_();model.actor[-1].bias[:16].zero_()
rows=[]
for mode in ['joint','normal']:
 c=SupportDeltaCoordinates(dict(mode=mode,reference_actor_state=reference),1,'cpu');c.reset(torch.tensor([0]),q,quat);action=c.action(q,known,model.actor_logits(public),scale,public);expected=bounded_motor_residual_action(q,known,original,scale);error=float((action-expected).abs().max());assert error<1e-7
 orth=float((c.basis.transpose(-1,-2)@c.basis-torch.eye(4)).abs().max());assert orth<1e-6
 extreme=c.action(q,known,torch.randn(1,20)*100,scale,public);targets=known.step(extreme);assert (targets[:,:16]-known.initial[:,:16]).abs().max()<.040001;assert torch.isfinite(targets).all();known.reset(torch.tensor([0]),q)
 rows.append(dict(mode=mode,initial_actual_original_actor_action_max_error=error,basis_orthogonality_max_error=orth,original_support_span_preserved=True))
p=D/'support-delta-coordinate-contract-v127.json';p.write_text(json.dumps({'passed':True,'results':rows,'scope':'Legal-onlyFK/frozeninheritedsupportmapping contract; no physics/contact/force performance claim'},indent=2));record('support_delta_coordinate_v127_contract_passed',evidence=str(p.relative_to(R)),next='Only launch shortmatched coordinatepilot ifv125 actualcontinuousresults stillfail');print(json.dumps(rows))
