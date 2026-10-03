"""Evaluation only: calibrated pair-normal forces, never controller inputs.

Installed native contact lambda is force, verified by known load at240/480Hz.
The fixture finds +normal acts on body0 and -normal on body1, despite the
documentation's body0->body1 phrase. Report normal contribution to axial force;
frictional traction cannot be reconstructed from net force or an unknown tangent.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation
FINGERS=('thumb','index','middle','ring','pinky')
class PairForceMeter:
    def __init__(self,gym,env,names,output,dt,thickness):
        self.gym=gym;self.env=env;self.names=names;self.dt=dt;self.thickness=thickness;self.samples=[]
        self.stream=(output/'contact-force-substeps.jsonl').open('w')
    def sample(self,t,states):
        force=np.zeros((5,2,3));counts=np.zeros((5,2),int);under=np.zeros(5);moments=np.zeros((5,3));all_moments=np.zeros((5,3));positions=[[] for _ in range(5)]
        knife_id=next(i for i,n in self.names.items() if n=='link_0');slider_id=next(i for i,n in self.names.items() if n=='link_1');kn=Rotation.from_quat(states[knife_id,3:7]).as_matrix();sl=Rotation.from_quat(states[slider_id,3:7]).as_matrix()
        for c in self.gym.get_env_rigid_contacts(self.env):
            first,second=int(c['body0']),int(c['body1']);a,b=self.names.get(first,''),self.names.get(second,'');pairs=[a,b]
            if not any(n in ['link_0','link_1'] for n in pairs) or float(c['lambda'])<=1e-6:continue
            finger=next((i for i,f in enumerate(FINGERS) if any('_'+f+'_' in n for n in pairs)),None)
            if finger is None:continue
            obj=first if a in ['link_0','link_1'] else second;part=0 if self.names[obj]=='link_0' else 1
            normal=np.array([c['normal'][x] for x in ['x','y','z']]);f=float(c['lambda'])*normal*(1 if obj==first else -1);force[finger,part]+=f;counts[finger,part]+=1
            key='localPos0' if obj==first else 'localPos1';local=np.array([c[key][x] for x in ['x','y','z']]);rot=Rotation.from_quat(states[obj,3:7]).as_matrix();world=rot@local+states[obj,:3]
            knife_point=kn.T@(world-states[knife_id,:3]);all_moments[finger]+=np.cross(knife_point,kn.T@f)
            if part==0 and local[1]<-.2*self.thickness:
                positive=max(0.,float(f@kn[:,1]));under[finger]+=positive;positions[finger].append(world.tolist())
                if positive>0:moments[finger]+=np.cross(local,kn.T@f)
        item={'time_s':t,'finger_force_normal_contribution_world_N':force,'contact_counts':counts,'slider_pressure_N':np.maximum(0,-force[:,1]@sl[:,1]),'slider_axial_normal_contribution_N':force[:,1]@sl[:,2],'underside_support_N':under,'underside_normal_moment_knife_Nm':moments,'all_contact_normal_moment_knife_Nm':all_moments,'underside_positions_world_m':positions}
        self.samples.append(item)
        if any(a<=t<b for a,b in [(12,12.25),(18,18.5),(23,23.5)]):self.stream.write(json.dumps({k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in item.items()})+'\n')
    def summary(self):
        z=self.samples;self.samples=[]
        positions=[]
        for finger in range(5):
            points=[p for x in z for p in x['underside_positions_world_m'][finger]]
            positions.append(np.mean(points,axis=0) if points else np.full(3,np.nan))
        return dict(pair_all_contact_normal_moment_knife_mean_Nm=np.mean([x['all_contact_normal_moment_knife_Nm'] for x in z],axis=0),pair_force_normal_contribution_world_mean_N=np.mean([x['finger_force_normal_contribution_world_N'] for x in z],axis=0),pair_underside_contact_position_world_mean_m=np.array(positions),pair_slider_pressure_mean_N=np.mean([x['slider_pressure_N'] for x in z],axis=0),pair_slider_pressure_min_N=np.min([x['slider_pressure_N'] for x in z],axis=0),pair_slider_pressure_max_N=np.max([x['slider_pressure_N'] for x in z],axis=0),pair_slider_axial_normal_contribution_mean_N=np.mean([x['slider_axial_normal_contribution_N'] for x in z],axis=0),pair_underside_support_mean_N=np.mean([x['underside_support_N'] for x in z],axis=0),pair_slider_contact_substep_fraction=np.mean([x['contact_counts'][:,1]>0 for x in z],axis=0),pair_body_contact_substep_fraction=np.mean([x['contact_counts'][:,0]>0 for x in z],axis=0),pair_underside_normal_moment_knife_mean_Nm=np.mean([x['underside_normal_moment_knife_Nm'] for x in z],axis=0),pair_force_substep_samples=len(z))
    def close(self):self.stream.close()
