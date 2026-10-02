import json,shutil,xml.etree.ElementTree as ET
import numpy as np
from scripts.record_wuji_real_size_goal import R,D,record
from scripts.wuji_width_contract import sha
from scripts.wuji_kinematics import WujiKinematics
from scripts.prepare_wuji_command_states import states_for_seed
name='knife_wuji_real_size_20261002';out=R/'assets/objects'/name;shutil.copytree(R/'assets/objects/knife_wuji_real_press_20261002',out)
# Photo-informed local shoulder; body/contact dimensions remain estimated except user L/W/T.
poly=[(-.015,-.0015),(.015,-.0015),(.015,-.0009),(.009,-.0008),(.004,.0015),(-.004,.0015),(-.008,-.0007),(-.015,-.0009)]
n=len(poly);verts=[(x,y,z) for x in [-.005,.005] for z,y in poly];faces=[[1,i+1,i] for i in range(2,n)]+[[n+1,n+i,n+i+1] for i in range(2,n)]
for i in range(n):j=(i+1)%n;faces.append([i+1,j+1,n+j+1,n+i+1])
# convex hull PhysX will span the shoulder; avoid claiming reconstructed concave mesh.
(out/'000/slider-shoulder.obj').write_text('\n'.join(['v %.8f %.8f %.8f'%v for v in verts]+['f '+' '.join(map(str,f)) for f in faces])+'\n')
meta=json.loads((out/'000/parameters.json').read_text());meta.update(round='real-size-student-adaptation-20261002',approximation='Photos and16 temporal video samples viewed. Central raised shoulder with lower end contact strips replaces long flat roof. Body135x16x12mm user-confirmed; slider10x3x30mm, axial position,50mm rail travel,mass/inertia remain estimates. Central body box retained; end rounding not at grasp contact. PhysX convex hull approximation.',urdf_sha256=sha(out/'000/mobility.urdf'))
(out/'000/parameters.json').write_text(json.dumps(meta,indent=2))
cfg=R/'isaacgymenvs/cfg/object'/(name+'.yaml');cfg.write_text('defaults:\n  - knife_wuji_bridge3_20260922\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000']\n")
shutil.copytree(R/'caches/initial_grasp/wuji/knife_wuji_real_press_20261002',R/'caches/initial_grasp/wuji'/name)
(D/'ASSETS.json').write_text(json.dumps({'real':{'object':name,'parameters':meta,'files':{str(p.relative_to(R)):sha(p) for p in [*out.rglob('*'),cfg] if p.is_file()}}},indent=2))
hand=WujiKinematics();seed=np.load(R/'research/real-knife-press-resistance-20261002/data/real/repaired-seeds.npy')[1];folder=D/'data/real';folder.mkdir(parents=True);np.save(folder/'adapted-seeds.npy',np.load(R/'research/real-knife-press-resistance-20261002/data/real/adapted-seeds.npy'))
entries=[]
for split,attempt,take,rng in [('dev',48,16,2026100251),('train',384,256,2026100252),('confirm',80,32,2026100253)]:
 states=states_for_seed(seed[None],rng,hand,trials=attempt);p=folder/(split+'-attempts.npy');np.save(p,states);entries.append(dict(split=split,attempted=attempt,take=take,seed=rng,source=3,path=str(p.relative_to(R)),sha256=sha(p)))
(D/'DATA.json').write_text(json.dumps(entries,indent=2));record('photo_informed_shape_and_fresh_states_prepared',evidence=str((D/'ASSETS.json').relative_to(R)),next='Static accept first valid source3 states; compare teacher and parent on new dev; confirmation policy closed')
