"""Finite PD preload references for a physically validated ring-surface gait.

Native contacts remain evaluation-only. Ring support requests the existing
0.7 N carrier reference through the original joint Jacobian/PD, and index keeps
its acquired preload. These are wrench proxies, not force measurements.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_direct_pickup import smooth

def main():
    p=argparse.ArgumentParser()
    for n in ['path','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--transport-normal',action='store_true',help='Rotate the acquired clamp wrench into the new support direction instead of applying its old lateral vector on the backface.')
    p.add_argument('--level-object-prior',type=Path,help='Use only a prior demonstrated object rotation for motor IK; no object-state writes.')
    p.add_argument('--level-duration-s',type=float,default=3.5)
    p.add_argument('--allow-held-thumb-prefix',action='store_true',help='An explicitly marked development prefix retains the original thumb carrier; require no free-thumb endpoint claim.')
    a=p.parse_args();d=json.load(a.path.open())
    if a.allow_held_thumb_prefix and not d.get('prefix_only'):raise ValueError('Held thumb permission requires an explicit prefix-only artifact')
    if not d['guard']['preflight_pass']:raise ValueError('Incomplete/blocked gait cannot be promoted to native motor')
    a.output.mkdir(parents=True,exist_ok=False);s=np.load(Path(d['source'])/'takeover.npz');trial,_,_=source_contacts(Path(d['source']));physics=json.load((trial/'physics.json').open());kp=np.array(physics['kp'])[7:];kd=np.array(physics['kd'])[7:];effort=np.array(physics['effort'])[7:]
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();q0=s['robot_q'][7:].astype(float);O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);times=np.array([x['time_s'] for x in d['diagnostics']]);hands=np.array([x['planned_hand_q'] for x in d['diagnostics']]);arms=np.array([x['planned_arm_q'] for x in d['diagnostics']]);velocity=np.gradient(hands,times,axis=0);max_effort_fraction=0.;captured=[]
    if a.level_object_prior:
        prior=np.load(a.level_object_prior/'trace.npz');goal=transform(prior['object'][0,:3],prior['object'][0,3:7]);goal[:3,3]=O[:3,3];rotation=Slerp([0,1],Rotation.from_matrix([O[:3,:3],goal[:3,:3]]));seed=arms[0].copy();iks=[]
        for i,v in enumerate(d['diagnostics']):
            oldO=np.array(v['expected_object_world']);L=np.linalg.inv(oldO)@k.forward(arms[i]);newO=O.copy();newO[:3,:3]=rotation(smooth((times[i]-.5)/a.level_duration_s)).as_matrix();seed,ik=k.solve_near(newO@L,seed,max_step=.16,minimum_margin=.06);iks.append(ik);arms[i]=seed;v['planned_arm_q']=seed.tolist();v['expected_object_world']=newO.tolist();d['rows'][i]['arm_q']=(seed+s['issued_target'][:7]-s['robot_q'][:7]).tolist()
        if max(v['position_m'] for v in iks)>.0005 or max(v['rotation_rad'] for v in iks)>.003:raise ValueError('World leveling IK blocked; do not execute')
        d['object_leveling_motor_ik']=dict(prior=str(a.level_object_prior),maximum_position_error_m=max(v['position_m'] for v in iks),minimum_joint_margin_rad=min(v['joint_margin_rad'] for v in iks),scope='Prior rotation only; motor references and original dynamics, no object write')
    record('functional_ring_gait_motor_start',[str(a.output)],config={'source':d['source'],'path':str(a.path),'ring_reference_proxy_N':.7,'transport_normal':a.transport_normal,'level_object_prior':str(a.level_object_prior) if a.level_object_prior else None,'uncertainty':'Can original finite PD transport acquired indexload and apply existing ring0.7N support along real housing/pad rolling surface, without thumb supporting at endpoint?','decision':'Guarded native tests actual contact/holding; failed supported endpoint -> revise grasp, no force gain sweep'},next_step='Motor proxy effort/rate/geometry guard then actual10s')
    carriers=[('hand_r_index_pad_link',np.arange(4),'index_material'),('hand_r_ring_pad_link',np.arange(12,16),'ring_material')]
    if 'middle_material' in d['diagnostics'][0]:carriers.append(('hand_r_middle_pad_link',np.arange(4,8),'middle_material'))
    if a.transport_normal:
        _,native,end=source_contacts(Path(d['source']));tc=[c for r in native if r['time_s']>end-.2 for c in r['contacts'] if c['hand_link']=='hand_r_thumb_link4'];tm=np.mean([c['position_hand_link_m'] for c in tc],0)
        for v in d['diagnostics']:v.setdefault('thumb_heel_material',tm.tolist())
        carriers.append(('hand_r_thumb_link4',np.arange(16,20),'thumb_heel_material'))
    for name,ids,key in carriers:
        def jacobian(q,L,m):
            def point(h):
                T=L@g.w.forward(h)[name];return T[:3,:3]@m+T[:3,3]
            P=point(q);J=np.empty((3,4))
            for j,idx in enumerate(ids):
                h=q.copy();h[idx]+=1e-5;J[:,j]=(point(h)-P)/1e-5
            return J
        m0=np.array(d['diagnostics'][0][key]);J0=jacobian(q0,L0,m0);tau=kp[ids]*(s['issued_target'][7:][ids]-q0[ids]);force=np.linalg.solve(J0@J0.T+np.eye(3)*1e-7,J0@tau);null=tau-J0.T@force;captured.append(dict(material_link=name,captured_deflection_wrench_proxy_N=force.tolist()))
        for i,(row,v) in enumerate(zip(d['rows'],d['diagnostics'])):
            h=hands[i];L=np.linalg.inv(np.array(v['expected_object_world']))@k.forward(arms[i]);m=np.array(v[key]);J=jacobian(h,L,m);F=force.copy()
            rollu=row.get('ring_roll_fraction',smooth((v['fraction']-.28)/.5));thumbu=row.get('thumb_release_fraction',smooth((rollu-.15)/.6))
            if a.transport_normal and 'index' in name:
                initialN=np.array([-1.,0.,0.]);newN=(1-rollu)*initialN+rollu*np.array([0.,1.,0.]);newN/=np.linalg.norm(newN);axis=np.cross(initialN,newN);angle=np.arccos(np.clip(initialN@newN,-1,1));R=Rotation.from_rotvec(axis/max(np.linalg.norm(axis),1e-12)*angle).as_matrix();F=R@force
            if a.transport_normal and 'thumb' in name:F=force*(1-thumbu)
            if 'ring' in name:
                T=L@g.w.forward(h)[name];N=T[:3,:3]@v['ring_normal_local'];N/=np.linalg.norm(N);u=rollu if a.transport_normal else v['fraction'];F=(1-u)*force+u*.7*N
            requested_tau=J.T@F+null*(1-thumbu if a.transport_normal and 'thumb' in name else 1.);max_effort_fraction=max(max_effort_fraction,float((abs(requested_tau)/effort[ids]).max()))
            preload=np.clip(requested_tau/kp[ids],-.3,.3);lead=np.clip(kd[ids]/kp[ids]*velocity[i,ids],-.07,.07);command=np.clip(h[ids]+preload+lead,g.w.lower[ids]+.06,g.w.upper[ids]-.06)
            if i==0:command=s['issued_target'][7:][ids]
            hh=np.array(row['hand_q']);hh[ids]=command;row['hand_q']=hh.tolist();row.setdefault('transported_support_proxy',{})[name]=dict(requested_wrench_proxy_N=F.tolist(),preload_rad=preload.tolist(),original_kd_velocity_lead_rad=lead.tolist())
    checker=HandIntersection();G=[]
    for t in np.arange(times[0],times[-1]+1e-5,.125):
        h=np.array([np.interp(t,times,hands[:,j]) for j in range(20)]);arm=np.array([np.interp(t,times,arms[:,j]) for j in range(7)]);W=k.forward(arm);F=g.w.forward(h);L=np.linalg.inv(O)@W
        table=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts)
        if a.level_object_prior:
            currentO=O.copy();currentO[:3,:3]=rotation(smooth((t-.5)/a.level_duration_s)).as_matrix();L=np.linalg.inv(currentO)@W
        G.append(dict(time_s=float(t),self=checker.inspect(h),table_clearance_m=table,thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(h,L,float(s['slider_q']),'thumb') if v['knife_link']=='link_0'),arm_margin_rad=float(np.minimum(arm-k.lower,k.upper-arm).min())))
    poses=np.c_[arms,hands];cmds=np.array([np.r_[v['arm_q'],v['hand_q']] for v in d['rows']]);summary=dict(path_guard=d['guard'],interpolated_self_frames=sum(bool(v['self']) for v in G),minimum_table_clearance_m=min(v['table_clearance_m'] for v in G),minimum_arm_margin_rad=min(v['arm_margin_rad'] for v in G),terminal_thumb_body_gap_m=G[-1]['thumb_body_gap_m'],maximum_requested_proxy_effort_fraction=max_effort_fraction,maximum_planned_rate_rad_s=float((abs(np.diff(poses,axis=0))/np.diff(times)[:,None]).max()),maximum_command_rate_rad_s=float((abs(np.diff(cmds,axis=0))/np.diff(times)[:,None]).max()),source_jump_rad=float(abs(cmds[0]-s['issued_target']).max()),scope='8Hz interpolated collision-hull/geometry evidence and joint-rate/URDF proxy effort; no dynamic/contact acceptance')
    summary['held_thumb_development_prefix']=a.allow_held_thumb_prefix
    summary['permits_native']=summary['interpolated_self_frames']==0 and summary['minimum_table_clearance_m']>.001 and summary['minimum_arm_margin_rad']>.05 and (a.allow_held_thumb_prefix or summary['terminal_thumb_body_gap_m']>.001) and max_effort_fraction<.5 and summary['maximum_planned_rate_rad_s']<1. and summary['maximum_command_rate_rad_s']<1.5 and summary['source_jump_rad']<1e-6
    d['development_abort_on_translation_m']=.018;d['functional_ring_support_proxy']=dict(captured=captured,ring_reference_N=.7,scope=__doc__);d['motor_guard']=summary
    (a.output/'motor.json').write_text(json.dumps(d,indent=2));(a.output/'guard.json').write_text(json.dumps(dict(summary=summary,rows=G),indent=2));print(json.dumps(summary),flush=True);e=record('functional_ring_gait_motor_terminal',[str(a.output/'motor.json'),str(a.output/'guard.json')],config=summary,next_step='Passing native permit -> immediately execute actual10s and inspect completecontacts/self/reserves')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    if not summary['permits_native']:raise SystemExit(2)

if __name__=='__main__':main()
