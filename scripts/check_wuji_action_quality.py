"""Recorded actual hand geometry audit, including affected nonadjacent pairs.

Convex intersections are measured by the radius of an inscribed ball in their
intersection, not a penetration depth. Adjacent housings/fixed pads are excluded.
The caller chooses temporal sampling; this is not continuous certification.
"""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform

DIGITS = ['index', 'middle', 'pinky', 'ring', 'thumb']

class HandIntersection:
    def __init__(self):
        self.g = DigitGeometry()
        self.parts = {}
        for n, meshes in self.g.meshes.items():
            self.parts[n] = [(v, ConvexHull(v).equations) for v, _ in meshes]
        self.pairs = []
        names = list(self.parts)
        for i, a in enumerate(names):
            for b in names[i+1:]:
                fa = next((f for f in DIGITS if '_'+f+'_' in a), None)
                fb = next((f for f in DIGITS if '_'+f+'_' in b), None)
                def index(n):
                    return 0 if 'base' in n else 5 if 'pad' in n else int(n[-1])
                if fa == fb and fa and abs(index(a)-index(b)) <= 1:
                    continue
                if 'base' in a+b and ('link1' in a+b or 'link2' in a+b):
                    continue
                self.pairs.append((a,b))
        self.component_keys=[(name,i) for name,parts in self.parts.items() for i in range(len(parts))]
        lookup={key:i for i,key in enumerate(self.component_keys)}
        self.component_pairs=[(a,ia,b,ib) for a,b in self.pairs for ia in range(len(self.parts[a])) for ib in range(len(self.parts[b]))]
        self.component_indices=np.array([(lookup[(a,ia)],lookup[(b,ib)]) for a,ia,b,ib in self.component_pairs])

    def inspect(self,q):
        frames = self.g.w.forward(q)
        world = {}
        for n, parts in self.parts.items():
            R,t = frames[n][:3,:3],frames[n][:3,3]
            world[n] = []
            for v,h in parts:
                normal = h[:,:3]@R.T
                vertices=v@R.T+t
                world[n].append((vertices,np.c_[normal,h[:,3]-normal@t],vertices.min(0),vertices.max(0)))
        bad=[]
        lower=np.array([world[name][i][2] for name,i in self.component_keys]);upper=np.array([world[name][i][3] for name,i in self.component_keys]);left,right=self.component_indices.T
        possible=np.all((upper[left]>=lower[right])&(upper[right]>=lower[left]),axis=1)
        for index in np.flatnonzero(possible):
            a,ia,b,ib=self.component_pairs[index];va,ha,_,_=world[a][ia];vb,hb,_,_=world[b][ib]
            axes=np.r_[ha[:,:3],hb[:,:3]]
            pa,pb=va@axes.T,vb@axes.T
            if np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()>=0:
                continue
            h=np.r_[ha,hb]
            result=linprog([0,0,0,-1],A_ub=np.c_[h[:,:3],np.ones(len(h))],b_ub=-h[:,3],bounds=[(None,None)]*4,method='highs')
            if result.success and result.x[3]>.0002:
                bad.append(dict(pair=[a,b],intersection_inscribed_radius_m=float(result.x[3])))
        return bad

def run(trial,output,stride=15):
    z=np.load(trial/'trace.npz');c=HandIntersection();w=c.g.w
    rows=[];fkmax=0.;qmargin=np.minimum(z['q']-w.lower,w.upper-z['q'])
    indices=sorted(set(range(0,len(z['time']),stride))|set(range(min(30,len(z['time']))))|{len(z['time'])-1})
    for i in indices:
        q=z['q'][i];F=w.forward(q);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);errors=[]
        for k,f in enumerate(['thumb','index','middle','ring','pinky']):
            X=W@F['hand_r_'+f+'_pad_link'];P=transform(z['pad_poses'][i,k,:3],z['pad_poses'][i,k,3:7]);errors.append(float(abs(X-P).max()))
        fkmax=max(fkmax,max(errors))
        rows.append(dict(frame=i,elapsed_s=float(z['time'][i]-z['time'][0]+1/30),stage_time_s=float(z['time'][i]),q=q.tolist(),issued_target=z['applied_target'][i,7:].tolist(),intersections=c.inspect(q),body_contacts=z['finger_body_contacts'][i].tolist(),slider_contacts=z['finger_slider_contacts'][i].tolist()))
    out=dict(trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),joint_names=w.names,original_lower=w.lower.tolist(),original_upper=w.upper.tolist(),fk_max_matrix_error=fkmax,minimum_actual_limit_margin_rad=float(qmargin.min()),affected_pair_intersection_frames=sum(bool(r['intersections']) for r in rows),sampled_frames=len(rows),stride=stride,rows=rows,limitations='Collision hull convex intersection; directly adjacent same-digit links/fixed pads and proximal palm mount housings excluded. >0.2mm intersection ball is a diagnostic threshold, not hardware tolerance or penetration depth. Sampled saved actual states; full axial contact force absent.')
    output.write_text(json.dumps(out,indent=2));return {k:v for k,v in out.items() if k!='rows'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stride',type=int,default=15);a=p.parse_args();print(json.dumps(run(a.trial,a.output,a.stride)))
