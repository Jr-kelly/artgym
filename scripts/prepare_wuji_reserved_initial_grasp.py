"""Focused wrist/three-carrier redesign of the actual initial tabletop grasp."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for n in ['source','prefix','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--margin',type=float,default=.08);a=p.parse_args();a.output.mkdir(exist_ok=False)
    s=np.load(a.source/'takeover.npz');g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics()
    O=transform(s['object_state'][:3],s['object_state'][3:7]);arm=s['robot_q'][:7].astype(float);h0=s['robot_q'][7:].astype(float);L0=np.linalg.inv(O)@k.forward(arm)
    _,native,_=source_contacts(a.source);names=['hand_r_index_link4','hand_r_middle_pad_link','hand_r_thumb_link4'];M={};P={};N={};F0=g.w.forward(h0)
    for n in names:
        C=[v for r in native for v in r['contacts'] if v['hand_link']==n and v['knife_link']=='link_0']
        M[n]=np.mean([v['position_hand_link_m'] for v in C],0);T=L0@F0[n];P[n]=T[:3,:3]@M[n]+T[:3,3]
        normal=np.mean([v['force_normal_contribution_knife_N'] for v in C],0);normal/=np.linalg.norm(normal);N[n]=(T[:3,:3].T@normal,normal)
    ids=np.r_[0:8,16:20];x0=np.r_[arm,h0[ids]];lo=np.r_[np.maximum(k.lower+.06,arm-.25),g.w.lower[ids]+a.margin];hi=np.r_[np.minimum(k.upper-.06,arm+.25),g.w.upper[ids]-a.margin]
    initial={f:g.gaps(h0,L0,float(s['slider_q']),f) for f in ['index','middle','thumb']}
    def decode(x):
        h=h0.copy();h[ids]=x[7:];W=k.forward(x[:7]);return W,np.linalg.inv(O)@W,h,g.w.forward(h)
    def table_clearance(W,F):
        return [float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts]
    def res(x):
        W,L,h,F=decode(x);r=[]
        for n in names:
            T=L@F[n];r.extend((T[:3,:3]@M[n]+T[:3,3]-P[n])*350)
            local,normal=N[n];r.extend((T[:3,:3]@local-normal)*.2)
        r.extend(min(0,v-.0002)*800 for v in table_clearance(W,F))
        for f in ['index','middle','thumb']:
            for gap,old in zip(g.gaps(h,L,float(s['slider_q']),f),initial[f]):
                threshold=min(-.00015,old['gap_lower_bound_m']) if gap['hand_link'] in names and gap['knife_link']=='link_0' else .0001
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*300)
            r.extend(min(0,v['gap_lower_bound_m']-.0001)*150 for v in g.self_gaps(h,f,certify_clearance_m=.0001))
        r.extend((x-x0)*.03);return np.array(r)
    e=record('initial_reserved_grasp_planning_start',[str(a.output)],config={'uncertainty':'Can acquired I4/Mpad/thumb4 contacts coexist with80mrad posture reserve and table-clear lower surfaces after wrist compensation?','margin_rad':a.margin,'physics_changed':False},next_step='Geometry permitting immediately fresh clamp/lift, not approval from IK')
    beg=time.time();fit=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=90,diff_step=1e-5);W,L,h,F=decode(fit.x)
    errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@M[n]+(L@F[n])[:3,3]-P[n])) for n in names}
    result=dict(source=str(a.source),arm_q=fit.x[:7].tolist(),hand_q=h.tolist(),wrist_in_knife=L.tolist(),material_points={n:v.tolist() for n,v in M.items()},carrier_errors_m=errors,table_clearance_m=min(table_clearance(W,F)),self=HandIntersection().inspect(h),actual_posture_margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min()),elapsed_s=time.time()-beg,scope='Planned pose only, acquired contacts and original motor preload; not native acceptance')
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps({n:v for n,v in result.items() if n not in ['arm_q','hand_q','wrist_in_knife','material_points']}))
    permit=not result['self'] and max(errors.values())<.0005 and result['table_clearance_m']>.0001
    if permit:
        prefix=json.loads(a.prefix.read_text());pick=prefix['direct_pickup'];old=json.loads(Path(pick['loading_motor_prior']).read_text());delta=h-h0
        for row in old['rows']:
            hand=np.array(row['hand_q']);hand+=delta*smooth((row['elapsed_s']-3.5)/1.5);row['hand_q']=np.clip(hand,g.w.lower,g.w.upper).tolist()
        old['scope']='Changed initial wrist/hand pose from acquired carrier solve; original issued preload retained, no physics writes'
        loading=a.output/'loading-motor.json';loading.write_text(json.dumps(old,indent=2));pick['loading_motor_prior']=str(loading)
        pick['wrist_in_knife']=L.tolist();pick['close_q']=(np.array(pick['close_q'])+delta).tolist()
        pick['open_q']=np.clip(np.array(pick['open_q'])+delta,g.w.lower+a.margin,g.w.upper-a.margin).tolist();pick['free_thumb_command_margin_rad']=a.margin
        prefix['duration_s']=10.;pick['continuous_stages']=pick['continuous_stages'][:1]
        (a.output/'prefix.json').write_text(json.dumps(prefix,indent=2))
    e=record('initial_reserved_grasp_planning_finished',[str(a.output/'candidate.json')],config=dict(carrier_errors_m=errors,table_clearance_m=result['table_clearance_m'],self=result['self'],margin_rad=result['actual_posture_margin_rad'],geometry_permits_native=permit),next_step='Passing pose fresh10s original load; failure identifies exact contact/table incompatibility')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(e['config'])+'\n')
    if not permit:raise SystemExit(2)

if __name__=='__main__':main()
