"""Force-balanced motor-target diagnostic on an existing seating path.

This is inverse statics, not a physics result. Contact forces are planning
variables only: the runner still writes only bounded finite-stiffness targets.
No additional force is applied to the object or robot.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import yaml
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.wuji_kinematics import WujiKinematics,FINGERS

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--preload',type=float,default=1.2,help='Planned thumb normal force N, not measured force.')
    p.add_argument('--gravity',type=float,nargs=3,default=[0,-9.81,0],help='Gravity in fixed knife coordinates.')
    a=p.parse_args();data=json.loads(a.input.read_text());w=WujiKinematics()
    kp=np.array(yaml.safe_load((ROOT/'isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').read_text())['dof_props']['stiffness'])
    mesh={}
    for f in FINGERS:
        for suffix in ['pad_link','link4']:
            n='hand_r_'+f+'_'+suffix
            v=np.array([np.fromstring(l[2:],sep=' ') for l in (ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')).read_text().splitlines() if l.startswith('v ')])
            mesh[n]=v[ConvexHull(v).vertices]
    # The goal is zero net wrench including knife gravity. COM is approximated
    # at knife root; record this assumption instead of calling it exact dynamics.
    gravity=np.array(a.gravity)*.035
    for row in data['waypoints']:
        t=np.array(row['wrist_in_knife']);q=np.array(row['touch_q']);fraction=row['alpha']
        frames=w.forward(q);normals=[];points=[];jac=[]
        angle=fraction*np.pi/2
        if data.get('normal_path')=='radial':
            angle=np.arctan2(.004,.0095)*fraction/.5 if fraction<.5 else np.arctan2(.004,.0095*(1-(fraction-.5)/.5))
        for j,f in enumerate(FINGERS):
            normal=np.array([np.cos(angle),np.sin(angle),0])*(1 if j==0 else -1)
            if 'contact_normals' in row:normal=np.asarray(row['contact_normals'][j],dtype=float)
            names=['hand_r_'+f+'_'+suffix for suffix in ['pad_link','link4']]
            pieces=[]
            for n in names:
                tf=t@frames[n];pieces.append(mesh[n]@tf[:3,:3].T+tf[:3,3])
            v=np.concatenate(pieces);projections=v@normal
            weights=np.exp(-(projections-projections.min())/.0003);weights/=weights.sum()
            pt=(v*weights[:,None]).sum(0);J=np.zeros((3,20))
            for index in [w.names.index('hand_r_'+f+'_joint'+str(jj)) for jj in range(1,5)]:
                qq=q.copy();qq[index]+=1e-5;ff=w.forward(qq);vv=[]
                for n in names:
                    tf=t@ff[n];vv.append(mesh[n]@tf[:3,:3].T+tf[:3,3])
                J[:,index]=((np.concatenate(vv)*weights[:,None]).sum(0)-pt)/1e-5
            normals.append(normal);points.append(pt);jac.append(J)
        normals=np.array(normals);points=np.array(points);jac=np.array(jac)
        pref=-normals*np.array([a.preload]+[a.preload/4]*4)[:,None]-gravity/5
        def wrench(f):
            f=f.reshape(5,3)
            return np.r_[f.sum(0)+gravity,np.cross(points,f).sum(0)/.05]
        def cone(f):
            f=f.reshape(5,3);pressure=-(f*normals).sum(1)
            tangent=f+pressure[:,None]*normals
            return np.r_[pressure-.06,2.5-pressure,pressure-np.linalg.norm(tangent,axis=1)]
        result=minimize(lambda f:((f.reshape(5,3)-pref)**2).sum(),pref.ravel(),method='SLSQP',
            constraints=[{'type':'eq','fun':wrench},{'type':'ineq','fun':cone}],options={'maxiter':150,'ftol':1e-10})
        if not result.success:raise ValueError((fraction,result.message))
        forces=result.x.reshape(5,3);tau=np.einsum('fij,fi->j',jac,forces)
        delta=tau/kp
        command=np.clip(q+delta,w.lower,w.upper)
        old=np.array(row['command_q'])
        blend=min(fraction/.1,1.)*min((1-fraction)/.1,1.)
        blend=blend*blend*(3-2*blend)
        row['command_q']=(old*(1-blend)+command*blend).tolist()
        row['inverse_statics']=dict(planned_forces_N=forces.tolist(),support_points=points.tolist(),outward_normals=normals.tolist(),
            motor_offset_rad=delta.tolist(),wrench_residual=wrench(result.x).tolist(),clipped_indices=np.where(abs(command-q-delta)>1e-8)[0].tolist())
    data['inverse_statics']=dict(preload_N=a.preload,gravity_in_knife=a.gravity,mass_kg=.035,friction_cone_mu=1.,
        center_of_mass='knife root approximation',boundary_blend_fraction=.1,
        validation='Planning only; predicted forces are not applied or measured. Physical trial required.')
    a.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(output=str(a.output),max_motor_offset=max(np.max(np.abs(r['inverse_statics']['motor_offset_rad'])) for r in data['waypoints']))))

if __name__=='__main__':main()
