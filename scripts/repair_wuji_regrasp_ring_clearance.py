"""One inactive-ring parking motor path, retaining other planned contact trajectories.

Ring need not hold a fictitious contact before it is seated. Original collision
meshes and limits certify the motor path; actual retention requires free-knife
continuous physics. No wrist/object state correction is performed online.
"""
import argparse,json,xml.etree.ElementTree as ET
from types import SimpleNamespace
from scripts.g2_kinematics import G2Kinematics
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(10-15*x+6*x*x)

def main():
 p=argparse.ArgumentParser();p.add_argument('--validate-only',action='store_true');p.add_argument('--path',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();j=json.loads(a.path.read_text());g=DigitGeometry();h=g.w;hand=np.asarray(j['hand_q']);ids=np.array([h.names.index('hand_r_ring_joint%d'%i) for i in range(1,5)]);old=hand[0,ids].copy();new=hand[-1,ids].copy();u=np.linspace(0,1,len(hand));sampleids=np.unique(np.linspace(0,len(hand)-1,17).astype(int));pairs=[('hand_r_ring_'+x,'hand_r_'+f+'_'+y) for x in ['link2','link3','link4','pad_link'] for f in ['thumb','index','middle','pinky'] for y in ['link2','link3','link4','pad_link']]
 def ring_curve(park):
  early=smooth(u/.25);late=smooth((u-.8)/.2);return old[None]+early[:,None]*(park-old)[None]+late[:,None]*(new-park)[None]
 def gaps(park):
  curve=ring_curve(park);out=[]
  for i in sampleids:
   q=hand[i].copy();q[ids]=curve[i];out.extend(z['gap_lower_bound_m'] for z in g.pair_gaps(q,pairs))
  return np.asarray(out)
 fit=SimpleNamespace(x=np.asarray(j['ring_parking_audit']['park_q_rad']),success=True,message='Revalidate existing optimizedpath with original velocity/table constraints') if a.validate_only else minimize(lambda x:float(np.sum((x-old)**2)+.2*np.sum((x-new)**2)),old,method='SLSQP',bounds=list(zip(h.lower[ids]+.005,h.upper[ids]-.005)),constraints=[dict(type='ineq',fun=lambda x:(gaps(x)-.00003)*1000)],options=dict(maxiter=100,ftol=1e-10))
 hand[:,ids]=ring_curve(fit.x);dt=np.diff(np.asarray(j['times_s']));rates=abs(np.diff(hand,axis=0))/dt[:,None];rows=[]
 for i in sampleids:
  negatives=[z for f in ['thumb','index','middle','ring','pinky'] for z in g.self_gaps(hand[i],f,certify_clearance_m=.000015) if z['gap_lower_bound_m']<.000015-1e-7];rows.append(dict(frame=int(i),uncertified_self_pairs=negatives))
 root=Path(__file__).resolve().parents[1];xml=ET.parse(root/h.config['asset']);limits={z.get('name'):float(z.find('limit').get('velocity')) for z in xml.findall('joint') if z.get('type')=='revolute'};velocity_limits=np.array([limits[n] for n in h.names]);tablegaps=[];k=G2Kinematics()
 for i in sampleids:
  wrist=k.forward(np.asarray(j['arm_q'][i]));frames=h.forward(hand[i])
  for name,meshes in g.meshes.items():
   m=wrist@frames[name]
   for v,n in meshes:
    vv=v@m[:3,:3].T+m[:3,3];ax=np.r_[np.eye(3),n@m[:3,:3].T];proj=(vv-np.array([.6,-.25,.725]))@ax.T;radius=abs(ax)@np.array([.3,.4,.025]);tablegaps.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max()))
 passed=bool(all(not r['uncertified_self_pairs'] for r in rows) and gaps(fit.x).min()>=.00003-1e-7 and bool(np.all(rates<velocity_limits[None])) and min(tablegaps)>.0003)
 j.update(hand_q=hand.tolist(),preflight_passed=passed,ring_parking_audit=dict(scope=__doc__,park_q_rad=fit.x.tolist(),optimizer_success=bool(fit.success),message=fit.message,minimum_ring_gap_m=float(gaps(fit.x).min()),maximum_motor_rate_rad_s=float(rates.max()),original_velocity_limits_passed=bool(np.all(rates<velocity_limits[None])),minimum_table_gap_m=float(min(tablegaps)),sampled_self_audit=rows,ring_support_during_transfer_claimed=False));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(dict(passed=passed,minimum_ring_gap_m=float(gaps(fit.x).min()),message=fit.message)));assert passed,'Ring parking path rejected'

if __name__=='__main__':main()
