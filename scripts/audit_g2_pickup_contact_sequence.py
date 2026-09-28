"""Read-only component/contact chronology from one existing pickup trace.

No simulator, new control trial, or measured-force inference. Component labels
come from recorded local contact points against the immutable collision hulls.
Points not uniquely on a surface remain ambiguous rather than guessed.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull
from scripts.g2_knife_geometry import KnifeGeometry


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    file=args.run/'partial-trace.npz'
    if not file.exists():file=args.run/'trace.npz'
    trace=np.load(file);n=len(trace['time']);knife=KnifeGeometry(args.spec)
    hulls={}
    for link,index,vertices in knife.parts:
        hulls[(link,index)]=ConvexHull(vertices).equations
    labels={('link_0',0):'handle',('link_1',0):'button_base',('link_1',1):'bump'}
    tables={name:np.zeros(n,dtype=int) for name in ['handle','button_base','bump','ambiguous','unclassified']}
    point_z={name:[[] for _ in range(n)] for name in tables}
    fingers=['thumb','index','middle','ring','pinky']
    hand_slider=np.zeros((n,5),dtype=int)
    hand_counts=np.zeros((n,5),dtype=int)
    tolerance=20e-6
    for line in (args.run/'knife-contact-pairs.jsonl').open():
        c=json.loads(line);step=c['step'];bodies=[c['body0'],c['body1']]
        kin=[i for i,b in enumerate(bodies) if b in ['link_0','link_1']]
        if len(kin)!=1:continue
        ki=kin[0];link=bodies[ki];other=bodies[1-ki]
        for fi,finger in enumerate(fingers):
            if '_'+finger+'_' in other:
                hand_counts[step,fi]+=1
                if link=='link_1':hand_slider[step,fi]+=1
        if other not in ['box','ground']:continue
        point=np.asarray(c['localPos'+str(ki)])
        matching=[]
        for (body,index),eq in hulls.items():
            if body!=link:continue
            # For normalized outward planes: max is <=0 inside the convex
            # polytope, zero on its boundary. No solver lambda used as force.
            surface=float((eq[:,:3]@point+eq[:,3]).max())
            if abs(surface)<=tolerance:matching.append(labels[(body,index)])
        label=matching[0] if len(matching)==1 else ('ambiguous' if matching else 'unclassified')
        tables[label][step]+=1;point_z[label][step].append(float(point[2]))
    all_table=sum(tables.values())
    assert np.array_equal(all_table,trace['knife_table_contacts']), 'Pair log/table trace counts disagree'
    assert np.array_equal(hand_counts,trace['finger_knife_contacts']), 'Pair log/hand trace counts disagree'
    assert np.array_equal(hand_slider,trace['finger_slider_contacts']), 'Pair log/slider trace counts disagree'
    lift=np.flatnonzero(trace['phase']=='lift');assert len(lift)
    events=[]
    for fi,finger in enumerate(fingers):
        absent=hand_counts[lift,fi]==0
        first=next((i for i in range(len(absent)-4) if absent[i:i+5].all()),None)
        events.append(dict(finger=finger,first_five_frame_absence_s=float(trace['time'][lift[first]]) if first is not None else None))
    rows=[]
    # Every lift frame, plus the preceding actual close endpoint; no cherry
    # picked windows and no revised phase reference.
    for i in [int(lift[0]-1),*map(int,lift)]:
        rows.append(dict(frame=i,time_s=float(trace['time'][i]),phase=str(trace['phase'][i]),
            finger_contact_counts=hand_counts[i].tolist(),finger_slider_contact_counts=hand_slider[i].tolist(),
            table_contact_counts={name:int(counts[i]) for name,counts in tables.items()},
            table_contact_local_z_range_m={name:[min(points[i]),max(points[i])] for name,points in point_z.items() if points[i]},
            slider_displacement_from_lower_m=float(trace['slider'][i]-knife.lower)))
    out=dict(scope='Offline audit of existing execution only; no new dynamics, policy, or force measurement',
        trace_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),contact_log_sha256=hashlib.sha256((args.run/'knife-contact-pairs.jsonl').read_bytes()).hexdigest(),
        asset_spec=str(args.spec),surface_label_tolerance_m=tolerance,
        pair_log_counts_match_trace=True,all_recorded_frames_have_table_contact=bool((all_table>0).all()),
        hand_slider_contact_rows=int(hand_slider.sum()),finger_order=fingers,
        component_table_contact_frames={name:int((count>0).sum()) for name,count in tables.items()},
        first_sustained_lift_contact_losses=events,rows=rows,
        causal_limit='Sequence localizes support loss; it does not prove edge placement, friction, servo response, or bump geometry is the unique cause.',
        physics_trials=0)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='rows'}))


if __name__=='__main__':main()
