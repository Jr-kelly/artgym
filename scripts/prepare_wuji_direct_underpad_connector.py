"""Replace a rejected reverse-source jump with a slow, verified motor connector."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--motor',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--refit-loaded-carriers',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);m=json.loads(a.motor.read_text());source=np.load(Path(m['source'])/'takeover.npz');g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();checker=HandIntersection()
    D=m['diagnostics'];R=m['rows'];d0=D[0];join=next(i for i,d in enumerate(D) if d['fraction']>0);d1=D[join];r1=R[join];O=np.array(d0['expected_object_world']);L0=np.linalg.inv(O)@k.forward(np.array(d0['planned_arm_q']));q0=np.array(d0['planned_hand_q']);F0=g.w.forward(q0);materials=d0['planned_support_materials'];targets={n:(L0@F0[n])[:3,:3]@np.array(v)+(L0@F0[n])[:3,3] for n,v in materials.items()};gaps0={f:g.gaps(q0,L0,float(source['slider_q']),f) for f in ['index','middle','thumb','ring','pinky']};rows=[];out=[];check=[]
    fitted_previous=q0.copy()
    record('direct_underpad_continuous_source_connector_start',[str(a.output)],config={'uncertainty':'Reverse validbranch has .291rad source-neighbor change; can 3s smooth interpolation preserve material supports, source gaps and selfclearance?', 'input':str(a.motor),'connector_duration_s':3.},next_step='Dense connector guard, no native if material/self/sourcegap fails')
    for t in np.linspace(0,3.5,29):
        u=smooth((t-.5)/3);h=(1-u)*q0+u*np.array(d1['planned_hand_q']);raw_hand=h.copy();arm=(1-u)*np.array(d0['planned_arm_q'])+u*np.array(d1['planned_arm_q']);W=k.forward(arm);L=np.linalg.inv(O)@W
        if a.refit_loaded_carriers and 0<u<1:
            for n,ids in [('hand_r_index_pad_link',np.arange(4)),('hand_r_middle_pad_link',np.arange(4,8)),('hand_r_thumb_link4',np.arange(16,20))]:
                prior=h[ids].copy();finger=n.split('_')[2];material=np.array(materials[n])
                def residual(x):
                    q=h.copy();q[ids]=x;F=g.w.forward(q);T=L@F[n];r=list((T[:3,:3]@material+T[:3,3]-targets[n])*350)
                    for v,old in zip(g.gaps(q,L,float(source['slider_q']),finger,frames=F),gaps0[finger]):r.append(min(0,v['gap_lower_bound_m']-min(.0001,old['gap_lower_bound_m']))*1500)
                    r.extend(min(0,v['gap_lower_bound_m']-.0001)*180 for v in g.self_gaps(q,finger,certify_clearance_m=.0001,frames=F));r.extend((x-prior)*.02);return np.array(r)
                # Continue the acquired loaded-digit branch, rather than
                # restarting a four-joint nullspace fit at every frame.
                lo=np.maximum(g.w.lower[ids]+.06,fitted_previous[ids]-.08)
                hi=np.minimum(g.w.upper[ids]-.06,fitted_previous[ids]+.08)
                lo=np.maximum(lo,prior-.12);hi=np.minimum(hi,prior+.12)
                fit=least_squares(residual,np.clip(fitted_previous[ids],lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=35,diff_step=1e-5);h[ids]=fit.x
            fitted_previous=h.copy()
        F=g.w.forward(h);errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@np.array(v)+(L@F[n])[:3,3]-targets[n])) for n,v in materials.items()};violations=[]
        for finger in gaps0:
            for v,old in zip(g.gaps(h,L,float(source['slider_q']),finger),gaps0[finger]):violations.append(max(0,min(.0001,old['gap_lower_bound_m'])-v['gap_lower_bound_m']))
        self=checker.inspect(h);table=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts)
        d=dict(time_s=float(t),fraction=float(u*d1['fraction']),planned_hand_q=h.tolist(),planned_arm_q=arm.tolist(),expected_object_world=O.tolist(),planned_support_materials=materials,support_errors_m=errors,thumb_error_m=0.,maximum_gap_violation_m=max(violations),self_intersections=self)
        cmd=(1-u)*source['issued_target']+u*np.r_[r1['arm_q'],r1['hand_q']];cmd[7:]+=h-raw_hand;rows.append(dict(time_s=float(t),arm_q=cmd[:7].tolist(),hand_q=cmd[7:].tolist()));out.append(d);check.append(dict(time_s=float(t),errors_m=errors,self=self,maximum_gap_deepening_m=max(violations),table_clearance_m=table,margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min())))
    shift=3.5-d1['time_s']
    for d,r in zip(D[join+1:],R[join+1:]):
        d=d.copy();r=r.copy();d['time_s']+=shift;r['time_s']+=shift;out.append(d);rows.append(r)
    adjacent=float(np.abs(np.diff(np.array([np.r_[d['planned_arm_q'],d['planned_hand_q']] for d in out]),axis=0)).max());guard=dict(maximum_connector_support_error_m=max(max(v['errors_m'].values()) for v in check),maximum_connector_gap_deepening_m=max(v['maximum_gap_deepening_m'] for v in check),connector_self_frames=sum(bool(v['self']) for v in check),minimum_table_clearance_m=min(v['table_clearance_m'] for v in check),minimum_margin_rad=min(v['margin_rad'] for v in check),largest_adjacent_joint_step_rad=adjacent,source_motor_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-source['issued_target']).max()),duration_s=out[-1]['time_s'])
    guard['preflight_pass']=guard['maximum_connector_support_error_m']<.0008 and guard['maximum_connector_gap_deepening_m']<.00005 and guard['connector_self_frames']==0 and guard['minimum_table_clearance_m']>.0002 and guard['minimum_margin_rad']>.049 and adjacent<.18 and guard['source_motor_jump_rad']<1e-6
    m.update(rows=rows,diagnostics=out,guard=guard,source_connector=dict(input=str(a.motor),evidence=check,scope=__doc__))
    (a.output/'motor.json').write_text(json.dumps(m,indent=2));record('direct_underpad_continuous_source_connector_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing actualsource connector -> original acquiredloadtransport and native immediately; firstguardfail needsgeometric connector repair')
    print(json.dumps(guard))
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
