"""Lateral approach below an overhanging knife end, then vertical lift.
Actual G2 arm/table and all open-hand/knife/table collisions are screened.
No attachment or simulator state setter is used to execute the motor path.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.wuji_kinematics import FINGERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--outward',type=float,default=.08);p.add_argument('--lift',type=float,default=.10);p.add_argument('--extract-outward',type=float,default=0.,help='Known motor-only outward extraction before full vertical lift; actual free-knife contact unproven');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    j=json.loads(a.plan.read_text());loc=json.loads(a.localization.read_text());world=np.asarray(loc['object_world_matrix']);w=np.asarray(j['wrist_in_knife']);goal=world@w;k=G2Kinematics();table=ArmTableCollision(.75);g=DigitGeometry(knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');openq=np.asarray(j['open_q']);qgrasp,e=k.solve(goal,np.asarray(loc['grasp_q']));assert e['position_m']<.001
    outside=goal.copy();outside[0,3]-=a.outward
    # Follow the near branch outward before planning its reverse approach.
    reverse,rd=plan_translation(k,qgrasp,outside,3.,1/30,table);start=reverse[-1];approach,ad=plan_translation(k,start,goal,3.,1/30,table)
    lifted=goal.copy();lifted[2,3]+=a.lift
    if a.extract_outward:
        assert 0<a.extract_outward<=.06
        extracted=goal.copy();extracted[0,3]-=a.extract_outward;extracted[2,3]+=.01
        first,fd=plan_translation(k,approach[-1],extracted,2.,1/30,table)
        lifted[0,3]-=a.extract_outward;second,sd=plan_translation(k,first[-1],lifted,2.,1/30,table)
        lift=first+second;ld=dict(extraction=fd,vertical=sd,scope='Two known motor-only segments; no object state assignment/contact trigger')
    else:lift,ld=plan_translation(k,approach[-1],lifted,4.,1/30,table)
    rows=[];frames=g.w.forward(openq);parts=g.knife_geometry.collision_parts(-.03267458688196273)
    for i,qarm in enumerate([start]+approach):
        wrist=k.forward(qarm);wo=np.linalg.inv(world)@wrist;knife_gap=min(g.minimum_gap(openq,wo,-.03267458688196273,f) for f in FINGERS);tablegaps=[]
        for name,meshes in g.meshes.items():
            mat=wrist@frames[name]
            for v,n in meshes:
                v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];pv=(v-np.array([.60,-.25,.725]))@axes.T;radius=abs(axes)@np.array([.30,.40,.025]);tablegaps.append(np.maximum(pv.min(0)-radius,-radius-pv.max(0)).max())
        row=dict(frame=i,knife_gap_m=knife_gap,table_gap_m=float(min(tablegaps)));rows.append(row)
    assert min(r['knife_gap_m'] for r in rows)>0, 'Open-hand lateral approach intersects knife'
    assert min(r['table_gap_m'] for r in rows)>.0003, 'Lateral approach intersects actual table'
    result=dict(args=vars(a),start_wrist_world=outside.tolist(),grasp_wrist_world=goal.tolist(),lift_wrist_world=lifted.tolist(),approach_q=[q.tolist() for q in [start]+approach],lift_q=[q.tolist() for q in [approach[-1]]+lift],audit_rows=rows,arm_audits=dict(reverse=rd,approach=ad,lift=ld),initial_estimate='Configured slider-up knife on tabletop edge; COM inside table, no body reset after initial placement',scope='Motor-path geometry only, actual contact/holding/operation untested')
    (a.output/'acquisition-path.json').write_text(json.dumps(result,default=str,indent=2));print(json.dumps(dict(frames=len(rows),min_knife_gap_m=min(r['knife_gap_m'] for r in rows),min_table_gap_m=min(r['table_gap_m'] for r in rows))))
if __name__=='__main__':main()
