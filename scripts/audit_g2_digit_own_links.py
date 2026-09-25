"""Check moving distal links against palm and nonadjacent proximal hulls."""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_wrist_plan import intersection_radius


def main():
    p=argparse.ArgumentParser()
    for name in ['source','plan','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--finger',required=True);p.add_argument('--start-stage',required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous audit')
    data=json.loads(a.source.read_text());plan=json.loads(a.plan.read_text());g=DigitGeometry();q=np.array(data['touch_q']);prefix='hand_r_'+a.finger+'_'
    pairs=[(prefix+x,'hand_r_base_link') for x in ['link3','link4','pad_link']]+[(prefix+'pad_link',prefix+x) for x in ['link1','link2']]
    baseline=[intersection_radius(g,q,*pair) for pair in pairs];bad=[];samples=0
    i=next(i for i,s in enumerate(plan['stages']) if s['name']==a.start_stage)
    for stage in plan['stages'][i:]:
        if stage['kind']!='move':continue
        indices=stage['moving_indices']
        if any(prefix not in g.w.names[j] for j in indices):raise ValueError('Expected only requested digit suffix')
        goal=q.copy();goal[indices]=stage['target']
        for u in np.linspace(0,1,21):
            samples+=1
            for pair,base in zip(pairs,baseline):
                radius=intersection_radius(g,q*(1-u)+goal*u,*pair)
                if radius is None or base is None or radius>base+1e-5:bad.append(dict(stage=stage['name'],alpha=float(u),pair=pair,radius_m=radius,baseline_m=base))
        q=goal
    out=dict(source=str(a.source),plan=str(a.plan),pairs=pairs,samples=samples,new_intersections=bad,passed=not bad,
        scope='Additional21samples/segment against5 distal-to-palm or nonadjacent own-link pairs. Does not replace other-digit/knife checks or certify continuous collision clearance.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
