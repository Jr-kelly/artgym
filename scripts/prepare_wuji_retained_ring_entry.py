"""Keep the acquired ring as a carrier at the retained thumb-path entrance.

This changes the transition target/support layout, not the retained push
weights or reference. Operating capability must be checked physically.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--entrance',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);record('retained_ring_entry_design_started',[str(a.source),str(a.entrance)],{'uncertainty':'Can retained thumb entrance carry using acquired Ring instead of forcing unreachable Pinky acquisition and retiring Ring?'},next_step='Reachable/safe Ring entry -> change reference and native transfer; blocked -> joint wrist/support adaptation, not static bias')
    g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');H=HandIntersection()
    z=np.load(a.source/'takeover.npz');entry=json.loads(a.entrance.read_text());L=np.linalg.inv(np.asarray(entry['object_in_wrist_actual']))
    q=np.asarray(entry['hand_q']);q[8:16]=z['robot_q'][15:23]
    verts=np.concatenate([v for v,_ in g.meshes['hand_r_ring_link4']]);previous=q[12:16].copy();begin=time.monotonic()
    def point(h):
        X=L@g.w.forward(h)['hand_r_ring_link4'];v=verts@X[:3,:3].T+X[:3,3]
        pr=v[:,1];w=np.exp((pr-pr.max())/.0002);return w@v/w.sum()
    def residual(x):
        h=q.copy();h[12:16]=x;p=point(h)
        r=[(p[1]+.004)*1000,max(abs(p[0])-.0090,0)*2500,max(p[2]+.035,0)*2000,max(-.067-p[2],0)*2000]
        r.extend((p-np.array([-.003,-.004,-.060]))[[0,2]]*12)
        r.extend((x-previous)*.05)
        r.extend(min(0,v['gap_lower_bound_m']-.0001)*1800 for v in g.self_gaps(h,'ring',certify_clearance_m=.0001))
        r.extend(min(0,v['gap_lower_bound_m']-.0003)*1600 for v in g.gaps(h,L,float(entry['slider_q_m']),'ring',certify_clearance_m=.0003) if v['hand_link'].endswith(('link1','link2','link3')))
        return np.asarray(r)
    fit=least_squares(residual,np.clip(previous,g.w.lower[12:16]+.025,g.w.upper[12:16]-.025),bounds=(g.w.lower[12:16]+.025,g.w.upper[12:16]-.025),max_nfev=120,diff_step=1e-5)
    q[12:16]=fit.x;pt=point(q);bad=H.inspect(q)
    result=dict(entry,hand_q=q.tolist(),issued_hand_target=q.tolist(),reference_entry_source=str(a.entrance),actual_grasp_source=str(a.source),ring_contact_geometry=pt.tolist(),self_intersections=bad,
                geometry_permits_native=abs(pt[1]+.004)<.0005 and abs(pt[0])<.0096 and -.068<pt[2]<-.033 and not bad,
                elapsed_s=time.monotonic()-begin,scope=__doc__)
    # Load targets must be captured/validated at this episode's actual entry;
    # a fitting point alone is not evidence that 55g can be carried.
    (a.output/'entry.json').write_text(json.dumps(result,indent=2));summary={k:result[k] for k in ['ring_contact_geometry','self_intersections','geometry_permits_native','elapsed_s']}
    record('retained_ring_entry_design_terminal',[str(a.output/'entry.json')],summary,next_step='Clear Ring entry -> joint contact-preserving transition/short policy then unchanged push; otherwise adapt wrist/support target')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
