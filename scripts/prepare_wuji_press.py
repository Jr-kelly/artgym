"""One approximate real knife and fresh small paired cohorts; no historical finals."""
import copy,json,shutil,xml.etree.ElementTree as ET
import numpy as np
from scripts.prepare_wuji_geometry import adapt
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_press_goal import R,D,record
from scripts.wuji_width_contract import sha
ROUND='real-knife-press-resistance-20261002'
def main():
 base=R/'assets/objects/knife_wuji_bridge3_20260922';meta=json.loads((base/'000/parameters.json').read_text());size=np.array([.016,.012,.135]);old=np.array(meta['handle_size']);origin=np.array(meta['slider_origin']);origin[1]+=.002
 name='knife_wuji_real_press_20261002';out=R/'assets/objects'/name;(out/'000').mkdir(parents=True,exist_ok=False)
 tree=ET.parse(base/'000/mobility.urdf')
 for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):box.set('size',' '.join(map(str,size)))
 tree.find("./joint[@name='slider']/origin").set('xyz',' '.join(map(str,origin)))
 # A convex side shoulder: upper face slopes down near the two axial ends.
 polygon=[(-.015,-.0015),(.015,-.0015),(.015,-.0003),(.010,.0015),(-.011,.0015),(-.015,.0002)]
 vertices=[(x,y,z) for x in [-.005,.005] for z,y in polygon];faces=[];n=len(polygon)
 faces += [[1,i+1,i] for i in range(2,n)]+[[n+1,n+i,n+i+1] for i in range(2,n)]
 for i in range(n):j=(i+1)%n;faces.append([i+1,j+1,n+j+1,n+i+1])
 mesh=out/'000/slider-shoulder.obj';mesh.write_text('\n'.join(['v %.8f %.8f %.8f'%v for v in vertices]+['f '+' '.join(map(str,f)) for f in faces])+'\n')
 for geo in tree.findall("./link[@name='link_1']/visual/geometry")+tree.findall("./link[@name='link_1']/collision/geometry"):
  for child in list(geo):geo.remove(child)
  ET.SubElement(geo,'mesh',filename='slider-shoulder.obj')
 urdf=out/'000/mobility.urdf';tree.write(urdf,encoding='utf-8',xml_declaration=True)
 meta.update(round=ROUND,label='real',handle_size=size.tolist(),slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),urdf_sha256=sha(urdf),total_size_lwt=[.135,.016,.015],approximation='Only135x16x12mm body measured; photos/video unavailable. Convex slider10x3x30mm with asymmetric axial shoulders approximated; no downward unlock.50mm travel,29g+6g masses and baseline effective inertia/contact friction inherited estimates.')
 (out/'000/parameters.json').write_text(json.dumps(meta,indent=2)+'\n');(out/'lbx.json').write_text(json.dumps({'000':size.tolist()+meta['slider_size']})+'\n')
 config=R/'isaacgymenvs/cfg/object'/(name+'.yaml');config.write_text('defaults:\n  - knife_wuji_bridge3_20260922\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000']\n")
 hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32);seeds=np.load(R/'research/multigrasp-20260928/data/candidates.npy')[:4];adapted=[];reports=[]
 for source,s in enumerate(seeds):
  state,rep=adapt(hand,s,size,origin,old);adapted.append(state);rep.update(source=source,thumb_reach_valid=rep['contact_errors_m'][0]<=.002);reports.append(rep)
 data=D/'data/real';data.mkdir(parents=True);np.save(data/'adapted-seeds.npy',adapted)
 cache=R/'caches/initial_grasp/wuji'/name/'000';cache.mkdir(parents=True);shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/grasp_state_metadata.json',cache/'grasp_state_metadata.json')
 for split in ['train','test']:(cache/split).mkdir();np.save(cache/split/'valid_grasps.npy',adapted)
 entries=[]
 for split,n,seed,take in [('pilot',8,2026100230,2),('dev',24,2026100231,8),('confirm',48,2026100232,16)]:
  states=np.concatenate([states_for_seed(np.array(adapted[s])[None],seed*100+s,hand,trials=n) for s in [0,3]]);p=data/(split+'-attempts.npy');np.save(p,states);entries.append(dict(split=split,seed=seed,attempts_per_source=n,sources=[0,3],take_per_source=take,path=str(p.relative_to(R)),sha256=sha(p)))
 (D/'DATA.json').write_text(json.dumps(dict(entries=entries,old_final_access=False,sources=[0,3],fallback_order=[1,2],rule='First static-valid fixed order, never policy filter; only0and3 initially'),indent=2)+'\n');(D/'GRASPS.json').write_text(json.dumps(dict(real=reports),indent=2)+'\n');(D/'ASSETS.json').write_text(json.dumps(dict(real=dict(object=name,parameters=meta,dimensions_mm_LWT=[135,16,12],files={str(p.relative_to(R)):sha(p) for p in [*out.rglob('*'),config] if p.is_file()})),indent=2)+'\n')
 record('approximate_real_asset_and_fresh_small_cohorts_prepared',evidence='research/'+ROUND+'/ASSETS.json',next='One static screen ofsources0/3; inspect zero-added-load C3200 andteacher then press pilot')
if __name__=='__main__':main()
