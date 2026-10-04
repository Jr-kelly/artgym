"""Park the optional ring across an estimated pickup/transfer motor trajectory.

Uses authored meshes and known planned joint/arm poses only. Changes no active
finger contact target, physical object, actuator or online policy input. Parking
is an initial known motor-plan choice, not an episode-internal state reset.
"""
import argparse,copy,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from types import SimpleNamespace
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--park-from',type=Path,help='Recheck a previously optimized legal park with complete table meshes, without refitting');p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 data={name:json.loads((a.input/(name+'.json')).read_text()) for name in ['pickup-plan','operation-plan','transfer','reference','acquisition','localization','audit']};pick=data['pickup-plan'];transfer=data['transfer'];g=DigitGeometry();h=g.w;k=G2Kinematics();ids=np.array([h.names.index('hand_r_ring_joint%d'%i) for i in range(1,5)]);poses=[];arm=np.asarray(data['acquisition']['approach_q'][-1]);way=pick['close_waypoints']
 for first,last in zip(way[:-1],way[1:]):
  for u in np.linspace(0,1,7):poses.append((arm,(1-u)*np.asarray(first['q'])+u*np.asarray(last['q'])))
 for i in np.unique(np.linspace(0,len(transfer['hand_q'])-1,17).astype(int)):poses.append((np.asarray(transfer['arm_q'][i]),np.asarray(transfer['hand_q'][i])))
 pairs=[('hand_r_ring_'+x,'hand_r_'+f+'_'+y) for x in ['link2','link3','link4','pad_link'] for f in ['thumb','index','middle','pinky'] for y in ['link2','link3','link4','pad_link']];matrices=[k.forward(arm) for arm,q in poses]
 def gaps(x,table=True):
  out=[]
  for wrist,(arm,q) in zip(matrices,poses):
   q=q.copy();q[ids]=x;out.extend(z['gap_lower_bound_m']-.00003 for z in g.pair_gaps(q,pairs))
   if table:
    frames=h.forward(q)
    for name,meshes in g.meshes.items():
     if not name.startswith('hand_r_ring_'):continue
     m=wrist@frames[name]
     for v,n in meshes:
      vv=v@m[:3,:3].T+m[:3,3];axes=np.r_[np.eye(3),n@m[:3,:3].T];proj=(vv-np.array([.6,-.25,.725]))@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);out.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max())-.0003)
  return np.asarray(out)
 original=np.asarray(pick['open_q'])[ids];start=np.asarray(transfer.get('ring_parking_audit',{}).get('park_q_rad',original));fit=SimpleNamespace(x=np.asarray(json.loads(a.park_from.read_text())['ring_parking_audit']['park_q_rad']),success=True,message='Rechecked existing park with full hand/table meshes') if a.park_from else minimize(lambda x:float(np.sum((x-original)**2)),np.clip(start,h.lower[ids]+.005,h.upper[ids]-.005),method='SLSQP',bounds=list(zip(h.lower[ids]+.005,h.upper[ids]-.005)),constraints=[dict(type='ineq',fun=lambda x:gaps(x)*1000)],options=dict(maxiter=80,ftol=1e-9))
 for plan in [pick,data['operation-plan']]:
  for key in ['open_q','touch_q','close_q']:
   q=np.asarray(plan[key]);q[ids]=fit.x;plan[key]=q.tolist()
  for row in plan['close_waypoints']:
   q=np.asarray(row['q']);q[ids]=fit.x;row['q']=q.tolist()
 hand=np.asarray(transfer['hand_q']);hand[:,ids]=fit.x;transfer['hand_q']=hand.tolist();rows=[]
 for row,(aq,q) in zip(data['audit']['geometry'],poses):
  q=q.copy();q[ids]=fit.x;remaining=copy.deepcopy(row);frames=h.forward(q);tablegaps=[]
  for name,meshes in g.meshes.items():
   mat=k.forward(aq)@frames[name]
   for v,n in meshes:
    vv=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];proj=(vv-np.array([.6,-.25,.725]))@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);tablegaps.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max()))
  remaining['minimum_table_gap_m']=min(tablegaps);remaining['uncertified_self_pairs']=[r for r in row['uncertified_self_pairs'] if 'hand_r_ring_' not in r['moving_link'] and 'hand_r_ring_' not in r['other_link']];rows.append(remaining)
 # Every changed pair is recertified across the same closure/transfer samples;
 # untouched active-finger/table certificates retain their original evidence.
 valid=float(gaps(fit.x).min())>=-1e-7 and all(not r['uncertified_self_pairs'] and r['minimum_table_gap_m']>.0003 for r in rows)
 passed=bool(valid and data['audit']['hand_rate_ok'] and data['audit']['arm_ik_ok'] and data['audit']['arm_rate_ok'] and data['audit']['arm_swept_table_recertified'] and data['reference']['all_feasible'])
 receipt=dict(scope=__doc__,optimizer_success=bool(fit.success),message=fit.message,park_q_rad=fit.x.tolist(),minimum_constraint_margin_m=float(gaps(fit.x).min()),ring_support_claimed=False,preflight_passed=passed,original_estimate=data['audit']['estimate'],samples=len(poses),non_ring_failures=[r for r in rows if r['uncertified_self_pairs'] or r['minimum_table_gap_m']<=.0003]);transfer.update(preflight_passed=passed,ring_parking_audit=receipt);data['audit'].update(preflight_passed=passed,hand_geometry_ok=valid,ring_parking_audit=receipt)
 for name,value in data.items():(a.output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(receipt));assert passed,'Estimated continuous motor path remains rejected; do not execute'
if __name__=='__main__':main()
