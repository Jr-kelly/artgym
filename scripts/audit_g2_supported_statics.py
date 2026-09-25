"""Quasi-static support feasibility along a geometric wrist suffix.

Uses actual start contact normals and material anchors. Force variables are
model predictions, not measurements or applied simulator forces. Includes
effort limits AND finite-stiffness position-command limits from runtime physics.
"""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous analysis')
    plan=json.loads(a.plan.read_text());meta=plan.get('supported_wrist_geometry',plan);d=json.loads(Path(meta['source']).read_text());trial=Path(d['source_trial'])
    t=np.load(d['source_trace']);step=d['source_step'];g=DigitGeometry();w=g.w
    physics=json.loads((trial/'physics.json').read_text());props=physics['robot_dof_properties'];ids=physics['hand_indices']
    kp=np.asarray(props['stiffness'])[ids];effort=np.asarray(props['effort'])[ids];mass=np.array(physics['knife_mass'])
    obj=transform(t['object'][step,:3],t['object'][step,3:]);gravity=obj[:3,:3].T@np.array([0,0,-9.81])*mass.sum()
    com=np.array([0,.0055,.010624586881962734+t['slider'][step]])*mass[1]/mass.sum();external=np.r_[gravity,np.cross(com,gravity)]
    raw=[json.loads(s) for s in (trial/'knife-contact-pairs.jsonl').read_text().splitlines()];normals=[]
    for anchor in meta['contact_anchors']:
        rows=[]
        for row in raw:
            if row['step']!=step:continue
            for side in [0,1]:
                if row['body'+str(side)]==anchor['link'] and row['body'+str(1-side)]=='link_0':
                    outward=np.array(row['normal'])*(1 if side==0 else -1);rows.append(obj[:3,:3].T@outward)
        normal=np.mean(rows,axis=0);normals.append(normal/np.linalg.norm(normal))
    results=[]
    initial=dict(degrees=0,nominal_q=d['touch_q'],wrist_in_knife=d['wrist_in_knife'])
    for row in [initial]+meta['rows']:
        q=np.array(row['nominal_q']);r=np.array(row['wrist_in_knife']);frames=w.forward(q);jac=[];points=[]
        for anchor in meta['contact_anchors']:
            link=anchor['link'];local=np.array(anchor['local_point']);frame=r@frames[link];point=frame[:3,:3]@local+frame[:3,3];J=np.zeros((3,20));points.append(point)
            for j in range(20):
                v=q.copy();v[j]+=1e-5;f=r@w.forward(v)[link];J[:,j]=(f[:3,:3]@local+f[:3,3]-point)/1e-5
            jac.append(J)
        for mu in [1.,2.,3.]:
            columns=[];torques=[];normal_select=[]
            for j,(normal,point,J) in enumerate(zip(normals,points,jac)):
                axis=np.eye(3)[np.argmin(abs(normal))];u=np.cross(normal,axis);u/=np.linalg.norm(u);v=np.cross(normal,u)
                for theta in np.arange(8)*np.pi/4:
                    force=-normal+mu*(np.cos(theta)*u+np.sin(theta)*v);columns.append(np.r_[force,np.cross(point,force)]);torques.append(J.T@force);normal_select.append(j)
            W=np.array(columns).T;T=np.array(torques).T;select=np.array([[int(j==v) for v in normal_select] for j in range(len(jac))])
            # At static equilibrium kp*(command-q)=J^T*object_contact_force.
            lo=np.maximum(-effort,kp*(w.lower-q));hi=np.minimum(effort,kp*(w.upper-q))
            for condition in ['wrench_only','effort_only','position_drives','position_drives_minload']:
                A=None;b=None
                if condition=='effort_only':A=np.r_[T,-T];b=np.r_[effort,effort]
                if condition=='position_drives':A=np.r_[T,-T];b=np.r_[hi,-lo]
                if condition=='position_drives_minload':A=np.r_[T,-T,-select];b=np.r_[hi,-lo,[-.03]*len(jac)]
                result=linprog(np.ones(len(columns)),A_eq=W,b_eq=-external,A_ub=A,b_ub=b,bounds=(0,None),method='highs')
                out=dict(degrees=row['degrees'],mu=mu,condition=condition,feasible=bool(result.success),solver_message=result.message)
                if result.success:
                    torque=T@result.x;command=q+torque/kp
                    out.update(modeled_normal_forces_N=(select@result.x).tolist(),modeled_torque_Nm=torque.tolist(),modeled_motor_command=command.tolist(),motor_offset_max_rad=float(np.max(np.abs(torque/kp))))
                results.append(out)
    a.output.write_text(json.dumps(dict(plan=str(a.plan),actual_start_normals_in_knife=[v.tolist() for v in normals],rows=results,
        assumptions='Quasi-static point contacts; fixed material anchors/normal; eight-ray friction cone mu1/2/3 diagnostic range. Four ablations: free wrench/effort/position-drive bounds/position-drive plus .03N per support. Source mass/COM/gravity, effort and position-drive stiffness/limits. Hand gravity off. No soft contact moments, no finger self-contact load. Predicted commands/forces not executed or measured.'),indent=2)+'\n')
    print(json.dumps([dict(degrees=v['degrees'],mu=v['mu'],condition=v['condition'],feasible=v['feasible'],normal_N=v.get('modeled_normal_forces_N'),offset=v.get('motor_offset_max_rad')) for v in results]))


if __name__=='__main__':main()
