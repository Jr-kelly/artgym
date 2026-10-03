"""Offline legal-feature reconstruction of retained actual G2 success/failure.

Object, slider and contact records are read only after estimation as labels.
No physical simulation or hardware command is issued.
"""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.wuji_goal_common import configuration
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_robust_learning import R800,TEACHER
from scripts.g2_legal_support_estimator import specification,LegalSupportEstimator
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--demos',type=Path,nargs='+',required=True);p.add_argument('--estimator',type=Path,required=True);p.add_argument('--interface-checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
    cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100376);kin=G2Kinematics();reports=[]
    for demo in a.demos:
        z=np.load(demo/'trace.npz');plan=json.loads((demo/'plan.json').read_text());cal=plan['handover_calibration'];assert cal and 'observed_q' in z and not plan['args']['thumb_script'];assert plan['args'].get('takeover_seconds',16)==16
        hand=json.loads((demo/'physics.json').read_text())['hand_indices'];policy=G2R800Policy(cfg,TEACHER,R800,residual_checkpoint=a.interface_checkpoint);head=LegalSupportEstimator(specification(a.estimator),policy.player.device);previous=np.zeros(20,np.float32);taken=False;predictions=[];indices=[];maximum_error=0.
        for i in range(len(z['time'])):
            q=z['observed_q'][i];policy.record(q,previous if taken else np.zeros(20,np.float32))
            if i<480:continue
            if not taken:
                policy.takeover_estimate(q,z['target'][i-1,hand],np.array(cal['object_in_wrist']),np.array(cal['slider_in_wrist']));taken=True
            issued=policy.known.issued.clone();goal=.04 if ((i-480)//150)%2==0 else 0.;policy.command(q,goal,wrist_gravity=kin.forward(z['arm_q'][i-1])[:3,:3].T@np.array([0.,0.,-1.]))
            public=policy.tensor(policy.last_public_features);packet=policy.tensor(policy.last_encoder_input);predictions.append(head(public,policy.player.model.a2c_network.priv_encoder,packet)[0].cpu().numpy());indices.append(i)
            # Keep actual recorded issued targets/actions, not counterfactual head
            # or policy actions. The estimator never changes the recorded chain.
            teacher=z['action'][i].copy();policy.known.issued[:]=issued;motor=policy.known.step(policy.tensor(teacher))[0].cpu().numpy();maximum_error=max(maximum_error,float(abs(motor-z['target'][i,hand]).max()));policy.last_action=teacher;previous=teacher
        assert maximum_error<2e-6,maximum_error;pred=np.array(predictions);ids=np.array(indices);times=z['time'][ids];asset=Path(__file__).resolve().parents[1]/plan['args']['knife_asset'];lower=float(ET.parse(asset).getroot().find("joint[@type='prismatic']/limit").get('lower'));actual_progress=z['slider'][ids-1]-lower;contact=z['finger_slider_contacts'][ids-1,0]>0;body=z['finger_body_contacts'][ids-1,0]>0;present=pred[:,7]>.5
        def mean(values,mask):return float(values[mask].mean()) if mask.any() else None
        errors=abs(pred[:,0]*.04-actual_progress)*1000;wrong_body=body&~contact
        report=dict(demo=str(demo),trace_sha256=hashlib.sha256((demo/'trace.npz').read_bytes()).hexdigest(),max_reconstructed_motor_target_error_rad=maximum_error,slider_lower_m=lower,progress_label='Absolute recordedq minusoriginalURDFlower; same training relative travel',progress_mae_mm=float(errors.mean()),progress_mae_exact_slider_contact_mm=mean(errors,contact),progress_mae_without_slider_contact_mm=mean(errors,~contact),exact_slider_pair_positive_count=int(contact.sum()),head_proxy_positive_fraction=float(present.mean()),proxy_vs_exact_pair_accuracy=float((present==contact).mean()),wrong_body_contact_count=int(wrong_body.sum()),proxy_false_positive_fraction_on_wrong_body=mean(present.astype(float),wrong_body),first_actual_no_slider_time_s=float(times[np.flatnonzero(~contact)[0]]) if (~contact).any() else None,first_head_proxy_absent_time_s=float(times[np.flatnonzero(~present)[0]]) if (~present).any() else None,scope='Offline legal observedq/action/issuedtarget/armFK replay; exact simulator pair-contact labels evaluated afterwards. A trained proximity/netcontact proxy is not an exact pair orforce sensor; no fresh physics or independent geometry claim.')
        np.savez_compressed(a.output/(demo.name+'.npz'),time=times,estimates=pred,actual_progress=actual_progress,exact_slider_contact=contact,body_contact=body);reports.append(report);print(json.dumps(report),flush=True)
    result=dict(estimator_sha256=hashlib.sha256(a.estimator.read_bytes()).hexdigest(),interface_checkpoint_sha256=hashlib.sha256(a.interface_checkpoint.read_bytes()).hexdigest(),reports=reports);(a.output/'report.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
