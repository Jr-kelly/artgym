"""Static PD/Jacobian estimates from an actual frame, never measured force."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous diagnostic')
    d=json.loads(a.source.read_text());trial=Path(d['source_trial']);t=np.load(d['source_trace']);i=d['source_step'];physics=json.loads((trial/'physics.json').read_text());ids=physics['hand_indices'];g=DigitGeometry()
    q=t['q'][i].astype(float);cmd=t['reference_targets'][i,ids];velocity=t['dof_velocity'][i,ids]
    stiffness=np.array(physics['robot_dof_properties']['stiffness'])[ids];damping=np.array(physics['robot_dof_properties']['damping'])[ids]
    tau=stiffness*(cmd-q)-damping*velocity
    obj=transform(t['object'][i,:3],t['object'][i,3:]);wrist=transform(t['wrist'][i,:3],t['wrist'][i,3:]);relative=np.linalg.inv(obj)@wrist
    contacts=[json.loads(line) for line in (trial/'knife-contact-pairs.jsonl').read_text().splitlines()];rows=[]
    for finger in ['thumb','index','middle','ring','pinky']:
        fids=[g.w.names.index('hand_r_'+finger+'_joint'+str(k)) for k in range(1,5)];samples=[]
        for row in contacts:
            if row['step']!=i:continue
            for side in [0,1]:
                if '_'+finger+'_' in row['body'+str(side)] and row['body'+str(1-side)]=='link_0':samples.append((row['body'+str(side)],np.array(row['localPos'+str(side)])))
        if not samples:rows.append(dict(finger=finger,contact_present=False));continue
        link=max(set(x[0] for x in samples),key=lambda name:sum(x[0]==name for x in samples));point=np.mean([x[1] for x in samples if x[0]==link],axis=0)
        def position(values):
            frame=relative@g.w.forward(values)[link];return frame[:3,:3]@point+frame[:3,3]
        J=np.zeros((3,4))
        for k,j in enumerate(fids):
            qp=q.copy();qp[j]+=1e-5;J[:,k]=(position(qp)-position(q))/1e-5
        force=np.linalg.lstsq(J.T,tau[fids],rcond=None)[0]
        rows.append(dict(finger=finger,contact_present=True,link=link,contact_count=len(samples),motor_reference_minus_q_rad=(cmd[fids]-q[fids]).tolist(),model_PD_torque_Nm=tau[fids].tolist(),
            model_least_squares_force_on_knife_N=force.tolist(),torque_residual_Nm=float(np.linalg.norm(J.T@force-tau[fids])),
            joint_limit_min_margin_rad=float(np.minimum(q[fids]-g.w.lower[fids],g.w.upper[fids]-q[fids]).min())))
    out=dict(source=str(a.source),source_trace=d['source_trace'],source_step=i,source_trace_sha256=hashlib.sha256(Path(d['source_trace']).read_bytes()).hexdigest(),
        physics_sha256=hashlib.sha256((trial/'physics.json').read_bytes()).hexdigest(),rows=rows,
        scope='Model estimates only: K*(target-q)-D*qdot and static mean-contact-point Jacobian least squares. NOT measured force or certified PhysX drive torque. Limit reactions, multiple contacts and implicit drive discretization can invalidate it. Hand gravity disabled as baseline; units Nm and N.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
