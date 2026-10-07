"""Correct only loaded-carrier FK curvature between certified motor knots."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--motor',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--coordinate-wrist',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    m=json.loads(a.motor.read_text());s=np.load(Path(m['source'])/'takeover.npz');D=m['diagnostics'];R=m['rows'];g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();checker=HandIntersection();O=np.array(D[0]['expected_object_world']);q0=np.array(D[0]['planned_hand_q']);L0=np.linalg.inv(O)@k.forward(np.array(D[0]['planned_arm_q']));F0=g.w.forward(q0);material=D[0]['planned_support_materials'];targets={n:(L0@F0[n])[:3,:3]@np.array(v)+(L0@F0[n])[:3,3] for n,v in material.items()};fingers=['index','middle','thumb'];gaps0={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in fingers};history=[]
    def evaluate(q,arm):
        W=k.forward(arm);L=np.linalg.inv(O)@W;F=g.w.forward(q);error=max(np.linalg.norm((L@F[n])[:3,:3]@np.array(v)+(L@F[n])[:3,3]-targets[n]) for n,v in material.items());deep=0.
        for f in fingers:
            for v,old in zip(g.gaps(q,L,float(s['slider_q']),f,frames=F),gaps0[f]):deep=max(deep,min(.0001,old['gap_lower_bound_m'])-v['gap_lower_bound_m'])
        return float(error),float(deep),checker.inspect(q)
    record('direct_loaded_interpolation_curvature_repair_start',[str(a.output)],config={'input':str(a.motor),'uncertainty':'Three between-knot loaded gaps deepen197–221µm despite all endpointguards; can local samebranch material reproject fix curvature?', 'change':'Only failing midpoint digit IK inserted; wrist/ring path and native physics fixed'},next_step='Adaptive midpoint guard, smoothpreload then native immediately')
    for iteration in range(4):
        additions=[];audit=[]
        for i in range(len(D)-1):
            t=(D[i]['time_s']+D[i+1]['time_s'])/2;arm=(np.array(D[i]['planned_arm_q'])+np.array(D[i+1]['planned_arm_q']))/2;q=(np.array(D[i]['planned_hand_q'])+np.array(D[i+1]['planned_hand_q']))/2;error,deep,self=evaluate(q,arm);audit.append(dict(time_s=t,error_m=error,deepening_m=deep,self=self))
            if error<.0008 and deep<.00005 and not self:continue
            original=q.copy();original_arm=arm.copy();L=np.linalg.inv(O)@k.forward(arm)
            carriers=[('hand_r_index_pad_link',np.arange(4)),('hand_r_middle_pad_link',np.arange(4,8)),('hand_r_thumb_link4',np.arange(16,20))]
            if a.coordinate_wrist:
                ids=np.r_[np.arange(8),np.arange(16,20)];x0=np.r_[arm,q[ids]];left=np.r_[D[i]['planned_arm_q'],np.array(D[i]['planned_hand_q'])[ids]];right=np.r_[D[i+1]['planned_arm_q'],np.array(D[i+1]['planned_hand_q'])[ids]];dt=(D[i+1]['time_s']-D[i]['time_s'])/2
                ring_gaps=g.gaps(q,L,float(s['slider_q']),'ring')
                def residual_all(x):
                    h=q.copy();h[ids]=x[7:];LL=np.linalg.inv(O)@k.forward(x[:7]);F=g.w.forward(h);r=[]
                    for n,indices in carriers:
                        T=LL@F[n];r.extend((T[:3,:3]@np.array(material[n])+T[:3,3]-targets[n])*350);f=n.split('_')[2]
                        for v,old in zip(g.gaps(h,LL,float(s['slider_q']),f,frames=F),gaps0[f]):r.append(min(0,v['gap_lower_bound_m']-min(.0001,old['gap_lower_bound_m']))*1500)
                        r.extend(min(0,v['gap_lower_bound_m']-.0001)*180 for v in g.self_gaps(h,f,certify_clearance_m=.0001,frames=F))
                    for v,old in zip(g.gaps(h,LL,float(s['slider_q']),'ring',frames=F),ring_gaps):r.append(min(0,v['gap_lower_bound_m']-min(.0002,old['gap_lower_bound_m']))*1500)
                    r.extend((x-x0)*.3);return np.array(r)
                lo=np.maximum.reduce([np.r_[k.lower+.06,g.w.lower[ids]+.06],x0-.03,left-dt,right-dt]);hi=np.minimum.reduce([np.r_[k.upper-.06,g.w.upper[ids]-.06],x0+.03,left+dt,right+dt])
                fit=least_squares(residual_all,np.clip(x0,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=60,diff_step=1e-5);arm=fit.x[:7];q[ids]=fit.x[7:]
            for n,ids in ([] if a.coordinate_wrist else carriers):
                prior=q[ids].copy();f=n.split('_')[2];point=np.array(material[n])
                def residual(x):
                    h=q.copy();h[ids]=x;F=g.w.forward(h);T=L@F[n];r=list((T[:3,:3]@point+T[:3,3]-targets[n])*350)
                    for v,old in zip(g.gaps(h,L,float(s['slider_q']),f,frames=F),gaps0[f]):r.append(min(0,v['gap_lower_bound_m']-min(.0001,old['gap_lower_bound_m']))*1500)
                    r.extend(min(0,v['gap_lower_bound_m']-.0001)*180 for v in g.self_gaps(h,f,certify_clearance_m=.0001,frames=F));r.extend((x-prior)*.1);return np.array(r)
                lo=np.maximum(g.w.lower[ids]+.06,prior-.06);hi=np.minimum(g.w.upper[ids]-.06,prior+.06);fit=least_squares(residual,np.clip(prior,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=35,diff_step=1e-5);q[ids]=fit.x
            error,deep,self=evaluate(q,arm)
            if error>.0008 or deep>.00005 or self:raise RuntimeError('Local midpoint refit failed at '+str(t)+' '+str((error,deep,self)))
            d=D[i].copy();d.update(time_s=t,fraction=(D[i]['fraction']+D[i+1]['fraction'])/2,planned_hand_q=q.tolist(),planned_arm_q=arm.tolist(),support_errors_m={n:error for n in material},maximum_gap_violation_m=deep,self_intersections=self)
            command=(np.r_[R[i]['arm_q'],R[i]['hand_q']]+np.r_[R[i+1]['arm_q'],R[i+1]['hand_q']])/2;command[:7]+=arm-original_arm;command[7:]+=q-original;row=dict(time_s=t,arm_q=command[:7].tolist(),hand_q=command[7:].tolist());additions.append((d,row))
        history.append(dict(iteration=iteration,audit=audit,inserted_times_s=[v[0]['time_s'] for v in additions]));print(json.dumps({'iteration':iteration,'inserted_times_s':history[-1]['inserted_times_s'],'maximum_audited_deepening_m':max(v['deepening_m'] for v in audit)}),flush=True)
        if not additions:break
        pairs=list(zip(D,R))+additions;pairs.sort(key=lambda v:v[0]['time_s']);D=[v[0] for v in pairs];R=[v[1] for v in pairs]
        (a.output/'refinement-progress.json').write_text(json.dumps(dict(rows=R,diagnostics=D,history=history,source=m['source'],scope='Partial planning, not preflight acceptance'),indent=2))
    else:raise RuntimeError('Curvature guard still fails after targeted midpoint refinement')
    poses=np.array([np.r_[d['planned_arm_q'],d['planned_hand_q']] for d in D]);steps=np.abs(np.diff(poses,axis=0));adjacent=float(steps.max());rate=float((steps/np.diff([d['time_s'] for d in D])[:,None]).max());guard=dict(maximum_support_error_m=max(v['error_m'] for v in history[-1]['audit']),maximum_loaded_gap_deepening_m=max(v['deepening_m'] for v in history[-1]['audit']),self_frames=sum(bool(v['self']) for v in history[-1]['audit']),largest_adjacent_joint_step_rad=adjacent,maximum_planned_joint_rate_rad_s=rate,source_motor_jump_rad=float(abs(np.r_[R[0]['arm_q'],R[0]['hand_q']]-s['issued_target']).max()),duration_s=D[-1]['time_s'],knots=len(D));guard['preflight_pass']=adjacent<.18 and rate<=1.000001 and guard['source_motor_jump_rad']<1e-6
    m.update(rows=R,diagnostics=D,guard=guard,loaded_interpolation_refinement=dict(input=str(a.motor),history=history,scope=__doc__));(a.output/'motor.json').write_text(json.dumps(m,indent=2));print(json.dumps(guard));record('direct_loaded_interpolation_curvature_repair_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing refined actualcarrier path -> capturedloadsmoothtransport/native realbackpadcontact immediately')
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
