"""Audit the selected lateral grip's opening/closing, retaining legacy flags.

Knife compression in motor targets is allowed only after touch. Self/table
intersection is never allowed. This is a sampled geometry certificate, not
servo tracking, contact force or successful physics.
"""
import argparse, json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_side_pickup_candidate import radius
from scripts.g2_kinematics import G2Kinematics


def separation(va,na,vb,nb):
    ca=va.mean(0);cb=vb.mean(0)
    sphere=float(np.linalg.norm(ca-cb)-np.linalg.norm(va-ca,axis=1).max()-np.linalg.norm(vb-cb,axis=1).max())
    if sphere>.000015:return sphere
    axes=np.r_[na,nb];a=va@axes.T;b=vb@axes.T
    return float(np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0)).max())


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--table-margin',type=float,default=.0003)
    p.add_argument('--acquisition-path',type=Path)
    a=p.parse_args();assert not a.output.exists()
    plan=json.loads(a.plan.read_text());loc=json.loads(a.localization.read_text())
    g=DigitGeometry(knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json')
    wrist=np.array(plan['wrist_in_knife']);world=np.array(loc['object_world_matrix'])
    parts=g.knife_geometry.collision_parts(plan['planning_slider_m'])
    graph={}
    for parent,child,*_ in g.w.joints:
        graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
    names=sorted(g.meshes);pairs=[]
    for i,name in enumerate(names):
        near={name}|graph.get(name,set());near|=set().union(*(graph.get(v,set()) for v in list(near)))
        pairs.extend((name,other) for other in names[i+1:] if other not in near)
    rows=[]
    segments=[('open_to_touch',plan['open_q'],plan['touch_q']),('touch_to_preload',plan['touch_q'],plan['close_q'])]
    if a.acquisition_path and not plan.get('lift_preload_height_m'):segments.append(('lift_hold',plan['close_q'],plan['close_q']))
    if 'post_lift_close_q' in plan:segments.append(('post_lift_preload',plan['close_q'],plan['post_lift_close_q']))
    if a.acquisition_path:
        acquisition=json.loads(a.acquisition_path.read_text());lift_path=np.array(acquisition['lift_q']);kin=G2Kinematics()
        base_height=kin.forward(lift_path[0])[2,3]
    for phase,first,last in segments:
        stage_world=world.copy()
        if phase=='post_lift_preload':stage_world[2,3]+=float(plan['post_lift_height_m'])
        coupled=phase=='post_lift_preload' and plan.get('lift_preload_height_m')
        for sample_fraction in np.linspace(0,1,121 if coupled or phase=='lift_hold' else 21):
            fraction=sample_fraction
            wrist_world=stage_world@wrist
            if coupled or phase=='lift_hold':
                u=sample_fraction**3*(10-15*sample_fraction+6*sample_fraction**2)
                index=u*(len(lift_path)-1);i=min(int(index),len(lift_path)-2);alpha=index-i
                aq=lift_path[i]*(1-alpha)+lift_path[i+1]*alpha;wrist_world=kin.forward(aq)
                if coupled:
                    first_height,last_height=plan['lift_preload_height_m'];height=wrist_world[2,3]-base_height
                    fraction=float(np.clip((height-first_height)/(last_height-first_height),0,1))
            q=np.array(first)*(1-fraction)+np.array(last)*fraction;frames=g.w.forward(q)
            hand={name:[(v@frames[name][:3,:3].T+frames[name][:3,3],n@frames[name][:3,:3].T) for v,n in meshes] for name,meshes in g.meshes.items()}
            self_bad=[];knife_bad=[];table_min=float('inf');table_min_link=None;minimum_world_z=float('inf')
            for first_name,last_name in pairs:
                for va,na in hand[first_name]:
                    for vb,nb in hand[last_name]:
                        if separation(va,na,vb,nb)<=0:
                            exact=radius(va,vb)
                            if exact is None or exact>1e-5:self_bad.append({'pair':[first_name,last_name],'intersection_radius_m':exact})
            for name,meshes in hand.items():
                for v,n in meshes:
                    vo=v@wrist[:3,:3].T+wrist[:3,3];no=n@wrist[:3,:3].T
                    vw=v@wrist_world[:3,:3].T+wrist_world[:3,3];nw=n@wrist_world[:3,:3].T
                    axes=np.r_[np.eye(3),nw];proj=(vw-np.array([.60,-.25,.725]))@axes.T
                    r=abs(axes)@np.array([.30,.40,.025]);gap=float(np.maximum(proj.min(0)-r,-r-proj.max(0)).max())
                    minimum_world_z=min(minimum_world_z,float(vw[:,2].min()))
                    if gap<table_min:table_min=gap;table_min_link=name
                    if phase=='open_to_touch':
                        for part in parts:
                            if separation(vo,no,part['vertices'],part['normals'])<=0:
                                exact=radius(vo,part['vertices'])
                                if exact is None or exact>1e-5:knife_bad.append({'link':name,'component':part['index'],'intersection_radius_m':exact})
            row={'phase':phase,'fraction':float(fraction),'sample_fraction':float(sample_fraction),'wrist_world_z_m':float(wrist_world[2,3]),'minimum_world_z_m':minimum_world_z,'table_min_link':table_min_link,'table_gap_m':table_min,'self_intersections':self_bad,'knife_intersections':knife_bad}
            rows.append(row)
    passed=all(r['table_gap_m']>=a.table_margin and not r['self_intersections'] and not r['knife_intersections'] for r in rows)
    out={'args':vars(a),'passed':passed,'rows':rows,'scope':'Selected lateral approach requires a separate unchanged acquisition-path certificate. Closing targets sampled21 persegment, original mesh/limits; table≥0.3mm predeclared before this audit, no exact self/openknife overlap. Intentional motor-target knife compression aftertouch only. Legacy0.5mm/openingerror/unused vertical flags retained separately, never reclassified. No physical success or force claim.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,default=str,indent=2))
    print(json.dumps({'passed':passed,'minimum_table_gap_m':min(r['table_gap_m'] for r in rows),'self_bad_frames':sum(bool(r['self_intersections']) for r in rows),'knife_bad_frames':sum(bool(r['knife_intersections']) for r in rows)}),flush=True)
    assert passed,'Rejected selected motor path; never execute'


if __name__=='__main__':main()
