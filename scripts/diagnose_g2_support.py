"""Offline support LP using actual contacts; model feasibility, never force measurement."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.g2_contact_geometry import DigitGeometry

def skew(v):return np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])

def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--phase',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--distributed',action='store_true',help='Retain each actual contact point instead of averaging each digit to one point.')
    p.add_argument('--assembly-roll-deg',type=float,default=0.,help='Hypothetical rigid hand+knife roll about knife length; changes gravity in this static model only, never simulator state.')
    a=p.parse_args()
    trace=a.trial/'trace.npz'
    if not trace.exists():trace=a.trial/'partial-trace.npz'
    t=np.load(trace);idx=int(np.flatnonzero(t['phase']==a.phase)[-1]);geom=DigitGeometry();q=t['q'][idx].astype(float)
    obj=transform(t['object'][idx,:3],t['object'][idx,3:]);wrist=transform(t['wrist'][idx,:3],t['wrist'][idx,3:]);relative=np.linalg.inv(obj)@wrist
    rows=[json.loads(s) for s in (a.trial/'knife-contact-pairs.jsonl').read_text().splitlines()];points=[]
    for finger in ['thumb','index','middle','ring','pinky']:
        contacts=[]
        for row in rows:
            if row['step']!=idx:continue
            for s in [0,1]:
                if row['body'+str(s)]=='link_0' and '_'+finger+'_' in row['body'+str(1-s)] and 'localPos'+str(s) in row:
                    normal=np.asarray(row['normal'])*(-1 if s==0 else 1);normal=normal@obj[:3,:3];normal/=np.linalg.norm(normal)
                    contacts.append((np.array(row['localPos'+str(s)]),normal,row['body'+str(1-s)],np.array(row['localPos'+str(1-s)])))
        if contacts and not a.distributed:
            link=contacts[0][2];contacts=[c for c in contacts if c[2]==link]
            point=np.mean([c[0] for c in contacts],axis=0);normal=np.mean([c[1] for c in contacts],axis=0);normal/=np.linalg.norm(normal)
            local=np.mean([c[3] for c in contacts],axis=0)
            contacts=[(point,normal,link,local)]
        for point,normal,link,local in contacts:
            J=np.zeros((3,20))
            for j in range(20):
                qq=q.copy();qq[j]+=1e-5;f=relative@geom.w.forward(qq)[link];g=relative@geom.w.forward(q)[link]
                J[:,j]=((f[:3,:3]@local+f[:3,3])-(g[:3,:3]@local+g[:3,3]))/1e-5
            points.append(dict(finger=finger,link=link,point=point,normal=normal,J=J))
    physics=json.loads((a.trial/'physics.json').read_text());limits=np.asarray(physics['robot_dof_properties']['effort'])[physics['hand_indices']]
    mass=np.array(physics['knife_mass']);slider_center=np.array([0,.0055,.010624586881962734+t['slider'][idx]])
    com=mass[1]*slider_center/mass.sum();gravity=obj[:3,:3].T@np.array([0,0,-9.81])*mass.sum()
    gravity=Rotation.from_euler('z',-a.assembly_roll_deg,degrees=True).apply(gravity)
    external=np.r_[gravity,np.cross(com,gravity)]
    tests=[]
    for omit in [[],['thumb'],['thumb','pinky']]:
        selected=[v for v in points if v['finger'] not in omit]
        for mu in [.5,1.,2.,3.]:
            columns=[];torques=[];names=[]
            for v in selected:
                normal=v['normal'];axis=np.eye(3)[np.argmin(abs(normal))];u=np.cross(normal,axis);u/=np.linalg.norm(u);z=np.cross(normal,u)
                for theta in np.arange(8)*2*np.pi/8:
                    force=-normal+mu*(np.cos(theta)*u+np.sin(theta)*z)
                    columns.append(np.r_[force,np.cross(v['point'],force)]);torques.append(v['J'].T@force);names.append(v['finger'])
            W=np.array(columns).T;T=np.array(torques).T
            result=linprog(np.ones(len(columns)),A_eq=W,b_eq=-external,A_ub=np.r_[T,-T],b_ub=np.r_[limits,limits],bounds=(0,None),method='highs')
            tests.append(dict(omit=omit,mu=mu,feasible=bool(result.success),solver_message=result.message,
                modeled_total_normal_force_N=float(result.fun) if result.success else None,
                modeled_joint_torque_max_Nm=float(abs(T@result.x).max()) if result.success else None,
                modeled_per_finger_normal_N={f:float(sum(v for n,v in zip(names,result.x) if n==f)) for f in set(names)} if result.success else None))
    out=dict(trial=str(a.trial),phase=a.phase,frame=idx,points=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in p.items() if k!='J'} for p in points],
             hypothetical_assembly_roll_deg=a.assembly_roll_deg,
             gravity_in_object_N=gravity.tolist(),com_in_object_m=com.tolist(),whole_thumb_geometry=geom.gaps(q,relative,t['slider'][idx]),support_tests=tests,
             contact_representation='all actual contact points' if a.distributed else 'mean point per digit',
             assumptions='Actual contacts at one frame; 8-ray inscribed friction cone, mu range0.5..3 (robot/knife inputs1/3; effective combine law not inferred). URDF effort caps from effective physics. Zero hand gravity baseline. Unilateral force balance about knife origin, no additional soft-finger moment. Static feasibility not proof of control or stable dynamics; model forces never measured.',
             thumb_command_error_rad=(t['targets'][idx,physics['hand_indices']][16:]-q[16:]).tolist())
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
