"""One geometry-only local grasp repair: relieve finger mesh penetration, preserve contact."""
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.record_wuji_press_goal import R,D,record
from scripts.prepare_wuji_geometry import meshes,penetration
from scripts.wuji_kinematics import WujiKinematics,FINGERS
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.wuji_width_contract import sha
hand=WujiKinematics();mesh=meshes(hand);seeds=np.load(D/'data/real/adapted-seeds.npy');size=np.array([.016,.012,.135]);origin=np.array([0,.0075,.010624586881962734]);repaired=[];reports=[]
for source in [0,3]:
 s=seeds[source].copy();q=s[:20].astype(float);r=Rotation.from_quat(s[43:47]);points,normals=hand.contacts(q);before=penetration(hand,mesh,s,size,origin)
 for k,f in enumerate(FINGERS):
  ids=[hand.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)];initial=q[ids].copy();parts={name:v for name,v in mesh.items() if '_'+f+'_' in name}
  def residual(x):
   z=q.copy();z[ids]=x;frames=hand.forward(z);depth=[]
   for name,vs in parts.items():
    fr=frames[name];v=r.inv().apply(vs@fr[:3,:3].T+fr[:3,3]-s[40:43])
    d=np.maximum(0,np.min(size/2-abs(v),axis=1)-.00065);depth.extend(d*600)
   p,n=hand.contacts(z);return np.r_[(p[k]-points[k])*70,(n[k]-normals[k])*.07,(x-initial)*.003,depth]
  fit=least_squares(residual,np.clip(initial,hand.lower[ids]+1e-6,hand.upper[ids]-1e-6),bounds=(hand.lower[ids],hand.upper[ids]),max_nfev=90);q[ids]=fit.x
 s[:20]=q;s[20:40]=np.clip(q+(seeds[source,20:40]-seeds[source,:20]),hand.lower,hand.upper);frames=hand.forward(q);s[55:70]=np.concatenate([frames[n][:3,3] for n in hand.config['track_links']]);repaired.append(s);reports.append(dict(source=source,before_depth_m=before,after_depth_m=penetration(hand,mesh,s,size,origin),contact_shift_m=np.linalg.norm(hand.contacts(q)[0]-points,axis=1).tolist()))
folder=D/'data/real';np.save(folder/'repaired-seeds.npy',repaired);entries=[]
for split,n,seed,take in [('pilot',16,2026100240,2),('dev',48,2026100241,8),('confirm',96,2026100242,16)]:
 rows=np.concatenate([states_for_seed(s[None],seed*100+source,hand,trials=n) for source,s in zip([0,3],repaired)]);p=folder/(split+'-repaired-attempts.npy');np.save(p,rows);entries.append(dict(split=split,seed=seed,sources=[0,3],attempts_per_source=n,take=take,path=str(p.relative_to(R)),sha256=sha(p)))
(D/'GRASP_REPAIR.json').write_text(json.dumps(dict(reason='Initial size adaptation left finger-mesh penetration and zero accepted independent pilot rows',reports=reports,entries=entries,policy_results_used=False,static_thresholds_unchanged=True),indent=2)+'\n');record('one_geometry_only_grasp_recipe_repair',evidence='research/real-knife-press-resistance-20261002/GRASP_REPAIR.json',next='Static accept repaired shared recipe once; preserve original rejections and do not select by policy success')
print(json.dumps(reports))
