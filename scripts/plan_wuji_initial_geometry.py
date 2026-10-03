"""Adapt a nominal grip/reference from an explicitly supplied initial estimate.

No physical asset, current object pose or contact state is read. Estimates must
be noisy measurements or labelled synthetic observations, never asset-ID rules.
The resulting targets still require actual continuous pickup/contact validation.
"""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry

def adapt(estimate,plan,support,reference):
    assert estimate['source'] and estimate['uncertainty_m']>0
    size=np.asarray(estimate['handle_size_WTL_m'],dtype=float)
    assert size.shape==(3,) and np.all(size>0)
    delta=np.asarray(estimate['slider_contact_shift_m'],dtype=float)
    assert delta.shape==(3,)
    center_delta=np.asarray(estimate.get('initial_object_center_shift_knife_m',[0,0,0]),dtype=float)
    assert center_delta.shape==(3,)
    base=np.array([.016,.012,.135]);g=DigitGeometry();h=g.w
    wrist=np.asarray(plan['wrist_in_knife']);normals=np.asarray(plan['contact_normals'])
    def surface(q,finger):
        i=['thumb','index','middle','ring','pinky'].index(finger)
        m=wrist@h.forward(q)['hand_r_'+finger+'_pad_link']
        v=np.concatenate([v for v,_ in g.meshes['hand_r_'+finger+'_pad_link']])@m[:3,:3].T+m[:3,3]
        projection=v@normals[i];weights=np.exp(-(projection-projection.min())/.0002);weights/=weights.sum()
        return weights@v,m[:3,0]
    def solve(q,finger,shift):
        origin,normal=surface(q,finger);target=origin+shift
        ids=[h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];start=q.copy()
        def residual(x):
            v=start.copy();v[ids]=x;p,n=surface(v,finger)
            return np.r_[(p-target)*100,(n-normal)*.12,(x-start[ids])*.002]
        fit=least_squares(residual,np.clip(q[ids],h.lower[ids]+1e-5,h.upper[ids]-1e-5),bounds=(h.lower[ids]+1e-5,h.upper[ids]-1e-5),max_nfev=150)
        result=q.copy();result[ids]=fit.x
        return result,float(np.linalg.norm(surface(result,finger)[0]-target))
    touch=np.asarray(plan['touch_q']);q=touch.copy();errors={}
    thumb_shift=center_delta+delta+np.array([0,(size[1]-base[1])/2,0])
    q,errors['thumb']=solve(q,'thumb',thumb_shift)
    for f in ['index','middle','pinky']:
        point,_=surface(touch,f)
        shift=center_delta+np.array([np.sign(point[0])*(size[0]-base[0])/2,-(size[1]-base[1])/2,point[2]*(size[2]/base[2]-1)])
        q,errors[f]=solve(q,f,shift)
    close=np.clip(q+np.asarray(plan['close_q'])-touch,h.lower+1e-4,h.upper-1e-4)
    opened=np.clip(np.asarray(plan['open_q'])+q-touch,h.lower+1e-4,h.upper-1e-4)
    result=copy.deepcopy(plan);result.update(touch_q=q.tolist(),close_q=close.tolist(),open_q=opened.tolist(),close_waypoints=[{'fraction':0.,'q':opened.tolist()},{'fraction':2/3,'q':q.tolist()},{'fraction':1.,'q':close.tolist()}],initial_geometry_estimate=estimate)
    pressure=copy.deepcopy(support)
    pressure['post_lift_target_q']=np.clip(q+np.asarray(support['post_lift_target_q'])-touch,h.lower+1e-4,h.upper-1e-4).tolist()
    ref=copy.deepcopy(reference);trajectory_errors=[]
    for row in ref['rows']:
        nominal=touch.copy();nominal[16:]=row['q_thumb'];adapted,error=solve(nominal,'thumb',thumb_shift)
        row['q_thumb']=adapted[16:].tolist();trajectory_errors.append(error)
        for key in ['minimum_knife_gap_m','minimum_self_gap_m','pad_facing_cosine','maximum_joint_step_rad','message','optimizer_success']:row.pop(key,None)
        row['point_error_m']=error;row['feasible']=error<.00025
    ref.pop('support_preload_schedule',None)
    ref['initial_geometry_estimate']=estimate
    ref['all_feasible']=all(row['feasible'] for row in ref['rows'])
    ref['all_feasible_scope']='IK accuracy and original joint limits only; original nominal collision certificates not reused. Full physical rollout required.'
    audit=dict(input=estimate,contact_errors_m=errors,trajectory_max_error_m=max(trajectory_errors),no_physical_asset_read=True,scope='Estimated initial geometry adaptation, original nominal joint-preload offsets retained; not force regulation, collision/contact feasibility unproven')
    return result,pressure,ref,audit

def main():
    p=argparse.ArgumentParser();p.add_argument('--estimate',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--support',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    values=adapt(*[json.loads(x.read_text()) for x in [a.estimate,a.plan,a.support,a.reference]])
    a.output.mkdir(parents=True,exist_ok=False)
    for name,value in zip(['motor-plan.json','support.json','reference.json','audit.json'],values):(a.output/name).write_text(json.dumps(value,indent=2))
    print(json.dumps(values[-1],indent=2))
if __name__=='__main__':main()
