"""Contact-changing ring reference to retained thumb entry; original physics.

The existing carrier rolls from a side/corner to the back face. Index/middle
and thumb motor priors remain loaded. This is an offline reference, never a
physical bearing claim; actual load-transfer is checked in a short episode.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--entry',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rolling-domain',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);record('retained_ring_contact_transition_started',[str(a.source),str(a.entry)],{'uncertainty':'Can the current Ring roll into back-face bearing before the side-clamp unloads, while keeping the retained thumb path?'},next_step='Fitted real surface path -> native carrying test, not another static gain/bias scan')
    z=np.load(a.source/'takeover.npz');entry=json.loads(a.entry.read_text());m=json.loads(a.reference.read_text());g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');k=G2Kinematics()
    O=transform(z['object_state'][:3],z['object_state'][3:7]);q0=z['robot_q'][7:].copy();verts=np.concatenate([v for v,_ in g.meshes['hand_r_ring_link4']]);kp=np.asarray(m.get('hand_kp',[.373522,.455924,.243684,.180270,.368709,.416425,.222186,.194276,.365533,.413931,.227294,.196472,.357182,.429773,.249302,.228503,.408447,.685860,.239111,.207361]))[12:16]
    W0=np.linalg.inv(O)@k.forward(z['robot_q'][:7]);n0=np.array([-1.,0,0]);n1=np.array([0.,1,0]);end=np.asarray(entry['ring_contact_geometry'])
    def point(h,W,n):
        X=W@g.w.forward(h)['hand_r_ring_link4'];v=verts@X[:3,:3].T+X[:3,3];pr=v@n;w=np.exp((pr-pr.max())/.0002);return w@v/w.sum()
    first=point(q0,W0,n0);rows=m['rows'];previous=q0[12:16].copy();audits=[]
    # Source measured-to-issued deformation is retained once, then rotated
    # into the new carrier normal through original Jacobian/K geometry.
    def jac(h,W,n):
        p=point(h,W,n);J=np.zeros((3,4))
        for j in range(4):hh=h.copy();hh[12+j]+=1e-5;J[:,j]=(point(hh,W,n)-p)/1e-5
        return J
    J0=jac(q0,W0,n0);tau=kp*(z['issued_target'][19:23]-q0[12:16]);force=np.linalg.lstsq(J0.T,tau,rcond=1e-6)[0];normal0=max(.05,float(force@n0))
    refgoal=json.loads(Path('runs/flat-table-20261006/direct/preparation/retained-push-call-path-v711/actual-entrance.json').read_text())
    qp=np.asarray(refgoal['hand_q']);qp_goal=np.asarray(refgoal['issued_hand_target']);Lgoal=np.linalg.inv(np.asarray(refgoal['object_in_wrist_actual']))
    # Use the already successful support load as a reference, not a new force
    # measurement or increased actuator limit. Native checks decide capacity.
    support_N=[]
    with Path('runs/contact-transfer-20261006/regression/nominal-125-video-v1/simulation/wrap-contact-physical-steps.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['time_s']<15.95:continue
            if r['time_s']>16.01:break
            support_N.append(sum(c['force_normal_contribution_knife_N'][1] for c in r['contacts'] if '_pinky_' in c['hand_link']))
    normal1=max(.1,float(np.mean(support_N)))
    duration=rows[-1]['time_s'];begin=time.monotonic()
    for i,r in enumerate(rows):
        u=r['time_s']/duration;f=u**3*(10-15*u+6*u*u);normal=n0*(1-f)+n1*f;normal/=np.linalg.norm(normal);target=first*(1-f)+end*f
        W=np.linalg.inv(O)@k.forward(r['arm_q']);h=q0*(1-f)+np.asarray(entry['hand_q'])*f
        def residual(x):
            hh=h.copy();hh[12:16]=x
            pt=point(hh,W,normal)
            if a.rolling_domain:
                # The body support plane goes through its actual corner.
                # A blended centroid cuts through the body during rotation.
                corner=np.array([.0095,-.004,pt[2]])
                rs=[float(normal@(pt-corner))*1200,max(abs(pt[0])-.0095,0)*1600,
                    max(abs(pt[1])-.004,0)*1600,max(pt[2]+.030,0)*1200,max(-.068-pt[2],0)*1200]
                rs.extend((x-previous)*.5)
            else:
                rs=list((pt-target)*1000);rs.extend((x-previous)*.02)
            rs.extend(min(0,v['gap_lower_bound_m']-.0001)*1800 for v in g.self_gaps(hh,'ring',certify_clearance_m=.0001))
            return np.asarray(rs)
        if i%3==0 or i==len(rows)-1:
            lower=g.w.lower[12:16]+.025;upper=g.w.upper[12:16]-.025
            if a.rolling_domain:
                lower=np.maximum(lower,previous-.15);upper=np.minimum(upper,previous+.15)
            fit=least_squares(residual,np.clip(previous,lower+1e-7,upper-1e-7),bounds=(lower,upper),max_nfev=25 if a.rolling_domain else 35,diff_step=1e-5);previous=fit.x
            h[12:16]=fit.x;J=jac(h,W,normal);reference_load=normal0*(1-f)+normal1*f
            target_ring=h[12:16]+(J.T@(normal*reference_load))/kp
            actual=point(h,W,normal)
            error=float(np.linalg.norm(actual-target))
            if a.rolling_domain:error=max(abs(float(normal@(actual-np.array([.0095,-.004,actual[2]])))),max(abs(actual[0])-.0095,0),max(abs(actual[1])-.004,0),max(actual[2]+.03,0),max(-.068-actual[2],0))
            audits.append({'time_s':r['time_s'],'touch_q':fit.x.tolist(),'motor_q':target_ring.tolist(),'point_error_m':error,'contact_point_knife_m':actual.tolist(),'normal_knife':normal.tolist(),'reference_normal_N':reference_load})
            (a.output/'ring-knots-partial.json').write_text(json.dumps(audits,indent=2))
    tt=np.asarray([r['time_s'] for r in audits]);motor=np.asarray([r['motor_q'] for r in audits])
    for r in rows:r['hand_q'][12:16]=[float(np.interp(r['time_s'],tt,motor[:,j])) for j in range(4)]
    rows[0]['hand_q'][12:16]=z['issued_target'][19:23].tolist();m['ring_transition']={'actual_source':str(a.source),'layout':'ExistingRing side/corner -> back, I/M carriers, Thumb body -> cap, Pinky free','normal_references_N':[normal0,normal1],'load_scope':'OriginalK/J motor preload reference, not measured total axial force or guaranteed bearing'}
    summary={'max_ring_surface_error_m':max(r['point_error_m'] for r in audits),'knots':len(audits),'normal_references_N':[normal0,normal1],'elapsed_s':time.monotonic()-begin,'scope':'Geometric reference only; no native or capacity acceptance'}
    (a.output/'motor.json').write_text(json.dumps(m,indent=2));(a.output/'ring-knots.json').write_text(json.dumps(audits,indent=2));(a.output/'result.json').write_text(json.dumps(summary,indent=2))
    record('retained_ring_contact_transition_terminal',[str(a.output/'motor.json'),str(a.output/'ring-knots.json')],summary,next_step='Check first contact-path bottleneck and original commandlimits; clear -> one native short bearing trial')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
