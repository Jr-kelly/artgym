"""Adapt only the once-estimated tabletop placement of an existing source1 grip.

Keep its independently matched post-lift prior and known bidirectional thumb
reference. This is not a new source/pool, live state adaptation or reset demo.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--table-end-inset-m',type=float,default=0.);p.add_argument('--thumb-open-extra-rad',type=float,default=0.);a=p.parse_args();assert 0<=a.table_end_inset_m<=.02 and 0<=a.thumb_open_extra_rad<=.45;a.output.mkdir(parents=True,exist_ok=False)
 base=Path('runs/wrap-force-20261004/comparison/four-sources-v1/source1')
 source=base/'negative-tangent-prepare-v4/motor-plan.json';plan=json.loads(source.read_text());plan['open_q'][16]-=a.thumb_open_extra_rad;plan['close_waypoints'][0]['q']=list(plan['open_q']);plan['source1_thumb_open_extra_rad']=a.thumb_open_extra_rad
 corner=Path('runs/wrap-force-20261004/planning/source-bounded-index-wrap-v8/direct-corner-v6/localization.json');loc=json.loads(corner.read_text());world=np.asarray(loc['object_world_matrix']);world[1,3]+=a.table_end_inset_m;loc['object_world_matrix']=world.tolist();loc['object'][1]+=a.table_end_inset_m;loc['table_end_inset_m']=a.table_end_inset_m;goal=world@np.asarray(plan['wrist_in_knife'])
 arm,error=G2Kinematics().solve(goal,np.asarray(loc['grasp_q']));(a.output/'ik-screen.json').write_text(json.dumps(dict(error=error,target=goal.tolist(),table_end_inset_m=a.table_end_inset_m),indent=2));assert error['position_m']<.001,error
 loc['grasp_q']=arm.tolist();loc['source']='Same corrected COM-inside original table corner, source1 matched pickup wrist, once-known placement only';loc['ik_error']=error
 plan['object_world_matrix']=world.tolist();plan['initial_geometry_estimate']=dict(width_m=.016,thickness_m=.012,length_m=.135,scope='Once-declared nominal original geometry; no live feedback')
 (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2));(a.output/'localization.json').write_text(json.dumps(loc,indent=2))
 for origin,target in [(base/'settled-v2/handover-calibration.json','calibration.json'),(base/'negative-tangent-prepare-v4/reference.json','reference.json')]: (a.output/target).write_bytes(origin.read_bytes())
 (a.output/'provenance.json').write_text(json.dumps(dict(source_plan=str(source),source_plan_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),corner=str(corner),scope=__doc__,postlift_prior='Existing offline physical source1 settled estimate; not pickup state setter or runtime truth',pool_expanded=False,physics_changed=False),indent=2));print(error)
if __name__=='__main__':main()
