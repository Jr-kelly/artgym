"""Collect legal-input support/progress estimation labels from actual TABLE chains.

Every environment remains in the same uninterrupted36s episode, including
failures. Current simulator state is label-only, never an actor input.
"""
import argparse,hashlib,json,time
from pathlib import Path
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic
from scripts.wuji_student_interface import tensor_hash
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
import torch,numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--envs',type=int,default=512);p.add_argument('--seed',type=int,default=2026100371);p.add_argument('--sample-stride',type=int,default=4);p.add_argument('--load-max',type=float,default=.2);p.add_argument('--detent-max',type=float,default=.2);p.add_argument('--strong-contact-label',action='store_true',help='Truthlabelonly: thumbproximity/netcontact timesactualslidernetcontact; no actorinput change');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);saved=torch.load(a.checkpoint,map_location='cuda');assert saved.get('history_features')
    scene=G2ContinuousScene(a.envs,a.seed,1.,load_max=a.load_max,detent_max=a.detent_max,reference_spec=saved['thumb_reference'],history_features=True,load_profile='mixed')
    model=ResidualActorCritic(170,197).to(scene.device);model.load_state_dict(saved['model']);model.eval();scale=torch.tensor(saved['action_scale'],device=scene.device);frozen_hash=tensor_hash(scene.player.model.state_dict());begin=time.monotonic()
    packets=[];features=[];labels=[];groups=[];times=[]
    initial={k:v.cpu().numpy() for k,v in dict(root=scene.root,dof=scene.dof,materials=scene.material_tensor,observation_bias=scene.observation_bias,delay=scene.delay,cal_object=scene.cal_object,cal_slider=scene.cal_slider,load_amplitude=scene.load_amplitude,detent_amplitude=scene.detent_amplitude,load_phase=scene.load_phase,load_profile_ids=scene.load_profile_ids,load_frequencies=scene.load_frequencies).items()};np.savez_compressed(a.output/'initial-snapshot.npz',**initial)
    try:
        for step in range(1080):
            public,critic=scene.features()
            if step>=480 and (step-480)%a.sample_stride==0:
                # Explicit134 measured/known channels plus existing16D legalSC.
                legal=torch.cat([public[:,:131],public[:,151:154],public[:,154:170]],-1)
                truth=critic[:,170:191];rotation=quat_mul(truth[:,3:7],quat_conjugate(scene.cal_object[:,3:7]));rotation=torch.where(rotation[:,3:4]<0,-rotation,rotation);sine=rotation[:,:3].norm(dim=-1,keepdim=True);angle=2*torch.atan2(sine,rotation[:,3:4].clamp_min(1e-8));rotvec=rotation[:,:3]*(angle/sine.clamp_min(1e-8))
                progress=(scene.dof[:,27,0]-scene.lower)/.04
                position=(truth[:,:3]-scene.cal_object[:,:3])/.01
                contact_label=scene.thumb_proximity()
                if a.strong_contact_label:contact_label*= (scene.contact[:,scene.slider_index].norm(dim=-1)>.01).float()
                target=torch.cat([progress[:,None].clamp(-.25,1.5),position.clamp(-4,4),(rotvec/.25).clamp(-4,4),contact_label[:,None]],-1)
                packets.append(scene.bridge.last_encoder_input.cpu().numpy().copy());features.append(legal.cpu().numpy().copy());labels.append(target.cpu().numpy().copy());groups.append(np.arange(a.envs,dtype=np.int32)%len(scene.instances));times.append(np.full(a.envs,step/30,np.float32))
            with torch.no_grad():residual=model.actor(public)
            scene.step(residual,scale,reset_failed=False,reset_finished=False)
            if step%150==0:print(json.dumps(dict(step=step,time_s=step/30)),flush=True)
        assert tensor_hash(scene.player.model.state_dict())==frozen_hash
        np.savez_compressed(a.output/'data.npz',packets=np.concatenate(packets),features=np.concatenate(features),labels=np.concatenate(labels),groups=np.concatenate(groups),times=np.concatenate(times))
        (a.output/'episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in scene.stats))
        report=dict(args=vars(a),rows=sum(len(x) for x in packets),physical_instances=scene.instances,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),base_tensor_hash=frozen_hash,data_sha256=hashlib.sha256((a.output/'data.npz').read_bytes()).hexdigest(),wall_seconds=time.monotonic()-begin,legal_packet='Actual50x40q/action+oncecalibratedinitial55+issuedtargets20+knowncommand1; same2076',legal_features='Public0:131,measuredarmFKgravity151:154,frozenSC16 fromsamepacket; no currenttruth orassetID',labels=('Evaluation/training only: sliderprogress/40mm,relativepositionerror/10mm,relativeorientationrotvec/0.25rad,'+('thumb+slider dualnetcontact proximityproxy.' if a.strong_contact_label else 'thumb-slider proximity/net-contact proxy.'))+' Position/rotation clipped4 to encode bounded support deviation, not exact fallen-object tracking.',selection=f'All{a.envs} environments atfixedtimes16–35.87s,including failedpickup/contact/drop, no episode outcome filtering',scope='Training-only actualG2 estimator data; independent012–015 remain closed')
        (a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps(report,default=str),flush=True)
    finally:scene.close()


if __name__=='__main__':main()
