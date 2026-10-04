"""Check software basis against original FK and bounded actual command memory."""
from isaacgym import gymapi
import json,numpy as np,torch
from pathlib import Path
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_support_delta_coordinates import SupportDeltaCoordinates
from scripts.wuji_known_controller import KnownWujiController
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004'); scene=json.loads(Path('research/antirotation-grasp-20261004/actual-table-lower-side-scene-v2.json').read_text());g=DigitGeometry();q=torch.tensor([scene['plan']['post_lift_close_q']],dtype=torch.float32);r=np.array(scene['calibration']['object_in_wrist'])[:3,:3];quat=torch.tensor([Rotation.from_matrix(r).as_quat()],dtype=torch.float32);ids=torch.tensor([0]);spec=dict(mode='contact-normal',reference_actor_state=None,controller_span_rad=.12,contact_normals_knife=scene['support_contact_normals_knife']);c=SupportDeltaCoordinates(spec,1,'cpu');c.reset(ids,q,quat);orth=float((c.basis.transpose(-1,-2)@c.basis-torch.eye(4)).abs().max());assert orth<1e-5
known=KnownWujiController(torch.tensor(g.w.lower,dtype=torch.float32),torch.tensor(g.w.upper,dtype=torch.float32),1);known.configure_support(.12,.025);known.reset(ids,q);scale=torch.tensor([.12]*16+[.15]*4);logits=torch.zeros_like(q);logits[:,0]=.5;positive=[]
for finger,joints in zip(c.fingers,c.ids):
 dq=c.basis[0,joints[0]//4,:,0].numpy()*.00001;v=q[0].numpy().copy();v[joints]+=dq;pad='hand_r_'+finger+'_pad_link';points=[]
 for x in [q[0].numpy(),v]:
  m=g.w.forward(x)[pad];verts=np.concatenate([p for p,_ in g.meshes[pad]]);world=verts@m[:3,:3].T+m[:3,3];normal=-r@np.array(spec['contact_normals_knife'][finger]);a=world@normal/.0002;a-=a.max();weight=np.exp(a);weight/=weight.sum();points.append(weight@world)
 displacement=float((points[1]-points[0])@normal);assert displacement>0,(finger,displacement);positive.append(dict(finger=finger,inward_displacement_m=displacement))
for i in range(6):
 before=known.issued.clone();action=c.action(q,known,logits,scale,torch.zeros((1,154)));motor=known.step(action);assert (motor[:,:16]-before[:,:16]).abs().max()<.025002;assert (known.last_executed_action[:,:16]*.12+q[:,:16]-motor[:,:16]).abs().max()<2e-6
out=B/'controller-compatibility-v2/contact-normal.json';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();result=dict(scope='Offline actual original FK/contact-normal basis and software rate/history only; no force/contact success',orthonormal_max_error=orth,positive_inward_fk_displacements=positive,actual_command_rate_history_passed=True);out.write_text(json.dumps(result,indent=2));print(json.dumps(result));record('contact_normal_coordinates_offline_check_passed',evidence=str(out),config=result,next='Use coordinate comparison only on new actual physical grasp and complete motor path, no old failed pilot extension')
