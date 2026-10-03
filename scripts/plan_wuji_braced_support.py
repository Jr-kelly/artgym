"""One coordinated opposite-side postlift support layout from public geometry.

Moving index alone previously retained its reaction but unloaded middle. This
candidate moves index and middle together, keeping pinky as the other side.
Soft collision-surface IK and static wrench are planning models only.
"""
import copy,json,os,pathlib,subprocess,sys
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry


def plan(motor,support,reference,output,calibration):
    output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=False)
    assert motor['initial_geometry_estimate']['source']
    g=DigitGeometry();h=g.w;wrist=np.asarray(motor['wrist_in_knife'])
    normals=np.asarray(motor['contact_normals']);touch=np.asarray(motor['touch_q']).copy()
    audits=[]
    def point(q,finger):
        frame=wrist@h.forward(q)['hand_r_'+finger+'_pad_link']
        v=np.concatenate([v for v,_ in g.meshes['hand_r_'+finger+'_pad_link']])@frame[:3,:3].T+frame[:3,3]
        normal=normals[['thumb','index','middle','ring','pinky'].index(finger)]
        p=v@normal;weights=np.exp(-(p-p.min())/.0002);weights/=weights.sum()
        return weights@v,frame[:3,0]
    for finger,x in [('index',.002),('middle',.001)]:
        original,axis=point(touch,finger);desired=original.copy();desired[0]=x
        ids=[h.names.index('hand_r_'+finger+'_joint'+str(i)) for i in range(1,5)]
        seed=touch.copy()
        def residual(value):
            q=seed.copy();q[ids]=value;p,a=point(q,finger)
            return np.r_[(p-desired)*100,(a-axis)*.12,(value-seed[ids])*.002]
        fit=least_squares(residual,np.clip(seed[ids],h.lower[ids]+1e-4,h.upper[ids]-1e-4),
            bounds=(h.lower[ids]+1e-4,h.upper[ids]-1e-4),max_nfev=250)
        touch[ids]=fit.x;actual,_=point(touch,finger);error=float(np.linalg.norm(actual-desired))
        audits.append(dict(finger=finger,original_m=original.tolist(),target_m=desired.tolist(),
            planned_m=actual.tolist(),error_m=error,joint_change_rad=(fit.x-seed[ids]).tolist()))
        assert error<.00025,audits[-1]
    candidate=copy.deepcopy(motor);candidate['touch_q']=touch.tolist();candidate['support_brace_audit']=audits
    (output/'touch-plan.json').write_text(json.dumps(candidate,indent=2))
    cmd=[sys.executable,'-m','scripts.plan_g2_contact_equilibrium','--plan',str(output/'touch-plan.json'),
        '--calibration',str(calibration),'--output',str(output/'equilibrium'),
        '--thumb-normal','1.5','--closed-slider-passive-limit']
    with (output/'planner.log').open('w') as log:
        result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Static wrench failed; receipt retained in '+str(output)
    wrench=json.loads((output/'equilibrium/motor-plan.json').read_text())
    target=np.clip(touch+1.25*(np.asarray(wrench['close_q'])-touch),h.lower+1e-4,h.upper-1e-4)
    config=copy.deepcopy(support);config.update(post_lift_target_q=target.tolist(),
        support_brace_audit=audits,transition_seconds=[12,14],
        scope='One coordinated index+middle opposite-side brace after unchanged TABLEpickup. Same1.5N staticpreference and1.25 offsettier, not measuredforce. Thumb path and original motor limits/collisions retained.')
    ref=copy.deepcopy(reference);ref['support_preload_schedule']=dict(seconds=[12,14],
        delta_q=(target-np.asarray(motor['close_q'])).tolist())
    for name,value in [('support.json',config),('reference.json',ref),('audit.json',dict(IK=audits,
        scope='Public-estimate offline surface/staticwrench plans only. No contact/force/collision certificate; actualcontinuousepisode required.'))]:
        (output/name).write_text(json.dumps(value,indent=2))
    return config,ref


def staged_transfer(motor,original_support,braced_support):
    """Withdraw each support before crossing; preserve original acquisition.

    No physical/contact state is read. The collision/contact feasibility of
    these public-geometry motor waypoints must be established by real rollout.
    """
    g=DigitGeometry();h=g.w;wrist=np.asarray(motor['wrist_in_knife'])
    root=pathlib.Path(__file__).resolve().parents[1]
    joints={j.get('name'):j for j in ET.parse(root/h.config['asset']).getroot().findall('joint')}
    velocity=np.asarray([float(joints[name].find('limit').get('velocity')) for name in h.names])
    normals=np.asarray(motor['contact_normals']);touch=np.asarray(motor['touch_q'])
    current=np.asarray(original_support['post_lift_target_q']).copy()
    final=np.asarray(braced_support['post_lift_target_q']);audits=[]
    rows=[dict(time_s=12.,q=motor['close_q']),dict(time_s=12.2,q=current.tolist())]
    def point(q,finger):
        frame=wrist@h.forward(q)['hand_r_'+finger+'_pad_link']
        v=np.concatenate([v for v,_ in g.meshes['hand_r_'+finger+'_pad_link']])@frame[:3,:3].T+frame[:3,3]
        normal=normals[['thumb','index','middle','ring','pinky'].index(finger)]
        weights=np.exp(-(v@normal-(v@normal).min())/.0002);weights/=weights.sum()
        return weights@v,frame[:3,0]
    for finger,new_x,times in [('index',.002,[12.5,12.9,13.2]),('middle',.001,[13.5,13.9,14.2])]:
        original,axis=point(touch,finger);ids=[h.names.index('hand_r_'+finger+'_joint'+str(i)) for i in range(1,5)]
        for x,time_s in zip([original[0],new_x],times[:2]):
            desired=original.copy();desired[0]=x;desired[1]-=.002
            seed=current.copy()
            def residual(value):
                q=seed.copy();q[ids]=value;p,a=point(q,finger)
                return np.r_[(p-desired)*100,(a-axis)*.12,(value-seed[ids])*.002]
            fit=least_squares(residual,np.clip(seed[ids],h.lower[ids]+1e-4,h.upper[ids]-1e-4),
                bounds=(h.lower[ids]+1e-4,h.upper[ids]-1e-4),max_nfev=250)
            current[ids]=fit.x;p,_=point(current,finger);error=float(np.linalg.norm(p-desired))
            assert error<.00025,(finger,time_s,error)
            rows.append(dict(time_s=time_s,q=current.tolist()));audits.append(dict(finger=finger,time_s=time_s,target_m=desired.tolist(),IK_error_m=error))
        current[ids]=final[ids]
        if finger=='middle':current=final.copy()
        rows.append(dict(time_s=times[2],q=current.tolist()))
    for first,last in zip(rows[:-1],rows[1:]):
        # Quintic smooth interpolation has peak slope1.875/duration.
        speed=np.abs(np.asarray(last['q'])-first['q'])*1.875/(last['time_s']-first['time_s'])
        assert (speed<=velocity+1e-6).all(),speed
    result=copy.deepcopy(braced_support);result['motor_waypoints']=rows
    result['staged_transfer_audit']=audits
    result['scope']='Sequential index/middle withdraw2mm, cross underbody, recontact using publicestimate only. Lasttarget14.2s leaves50actualconstant-target frames before16s; samegravity/motors/fullcollisions. IK is not contact/collision certification.'
    return result
