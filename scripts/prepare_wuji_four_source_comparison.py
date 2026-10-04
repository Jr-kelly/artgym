"""Fixed representatives of four existing sources; coordinate mapping, not pool expansion.

This prepares matched initial estimates and motor plans. Geometry planning and
held-reset physics are diagnostics; neither is continuous pickup success.
"""
import argparse, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_kinematics import WujiKinematics, FINGERS

R = Path(__file__).resolve().parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    poolpath=R/'caches/initial_grasp/wuji/knife_wuji_robust_family_20261003/000/train/valid_grasps.npy'
    metadata=poolpath.parent.parent/'grasp_state_metadata.json'
    assert json.loads(metadata.read_text())['pose_frame']=='hand_base'
    pool=np.load(poolpath);assert pool.shape==(192,75)
    h=WujiKinematics();k=G2Kinematics()
    handxml=ET.parse(R/h.config['asset']).getroot()
    g2xml=ET.parse(R/'assets/robots/g2_wuji/g2_wuji.urdf').getroot()
    # The mounting chain ends at hand_r_base_link. Downstream hand joints must
    # preserve parent/child, origin, axis and limits, with name-based indices.
    g2j={j.get('name'):j for j in g2xml.findall('joint')}
    checks=[]
    for j in handxml.findall('joint'):
        n=j.get('name');assert n in g2j,n
        gj=g2j[n];assert j.get('type')==gj.get('type'),n
        for tag in ['parent','child','origin','axis','limit']:
            x,y=j.find(tag),gj.find(tag)
            assert (x is None)==(y is None),(n,tag)
            if x is not None:assert x.attrib==y.attrib,(n,tag,x.attrib,y.attrib)
        checks.append(n)
    world=transform([.3015,-.25,.7561],[np.sqrt(.5),0,0,np.sqrt(.5)])
    rows=[]
    for source,index in enumerate([0,48,96,144]):
        s=pool[index].astype(float);folder=a.output/('source%d'%source);folder.mkdir()
        relative=transform(s[40:43],s[43:47]);w=np.linalg.inv(relative)
        q=s[:20];closed=s[20:40];assert np.all(q>=h.lower) and np.all(q<=h.upper)
        assert np.all(closed>=h.lower) and np.all(closed<=h.upper)
        points,_=h.contacts(q);local=(points-relative[:3,3])@relative[:3,:3]
        normals=[]
        for i,point in enumerate(local):
            axis=1 if i==0 else int(np.argmax(np.abs(point)/np.array([.008,.006,.0675])))
            n=np.zeros(3);n[axis]=1 if point[axis]>=0 else -1;normals.append(n.tolist())
        assert np.allclose(normals[0],[0,1,0]),'Thumb orientation requires a separately matched planner'
        opened=np.clip(closed*.3,h.lower,h.upper)
        opened[16:]=np.clip(closed[16:]-[.35,0,.25,0],h.lower[16:],h.upper[16:])
        arm,e=k.solve(world@w)
        lifted=world@w;lifted=lifted.copy();lifted[2,3]+=.16;armlift,el=k.solve(lifted,arm)
        roundtrip=np.linalg.inv(k.forward(armlift))@(k.forward(armlift)@relative)
        assert np.max(abs(roundtrip-relative))<1e-12
        slider=transform(s[47:50],s[50:54])
        expected=relative@transform([0,.0075,.010624586881962734+s[54]])
        slider_error=float(np.linalg.norm(slider[:3,3]-expected[:3,3]))
        assert slider_error<1e-6,slider_error
        plan=dict(source=source,cache_index=index,scope=__doc__,wrist_in_knife=w.tolist(),touch_q=q.tolist(),close_q=closed.tolist(),open_q=opened.tolist(),active_fingers=list(FINGERS),contact_normals=normals,contact_points=local.tolist(),planning_slider_m=float(s[54]),close_waypoints=[dict(fraction=0.,q=opened.tolist()),dict(fraction=2/3,q=q.tolist()),dict(fraction=1.,q=closed.tolist())],initial_geometry_estimate=dict(handle_size_WTL_m=[.016,.012,.135],slider_size_WTL_m=[.01,.003,.03],slider_contact_shift_m=[0,0,0]),object_world_matrix=world.tolist())
        (folder/'motor-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        (folder/'localization.json').write_text(json.dumps(dict(object_world_matrix=world.tolist(),grasp_q=arm.tolist()),indent=2)+'\n')
        (folder/'arm-seed.json').write_text(json.dumps(arm.tolist())+'\n')
        # Initial slider estimate is authored from this representative's rail
        # state and geometry, not another source's cached relative transform.
        (folder/'handover-calibration.json').write_text(json.dumps(dict(object_in_wrist=relative.tolist(),slider_in_wrist=slider.tolist(),scope='Once-loaded representative initial geometry estimate; no live truth feedback'),indent=2)+'\n')
        np.save(folder/'representative.npy',s[None])
        rows.append(dict(source=source,index=index,original_train_rows=[source*48,(source+1)*48-1],original_test_rows=[source*12,(source+1)*12-1],representative_sha256=sha(folder/'representative.npy'),slider_coordinate_error_m=slider_error,object_roundtrip_max_abs=float(np.max(abs(roundtrip-relative))),arm_grasp_ik=e,arm_lift_ik=el,contact_normals=normals,plan=str(folder/'motor-plan.json')))
    result=dict(pool_sha256=sha(poolpath),sources=4,records=192,records_per_source=48,selection='First existing train perturbation in each original source; no filtering, no expansion',cache_frame='hand_base',hand_joint_chain_exact=checks,hand_order=h.names,arm_order=k.names,geometry_split=dict(train=list(range(12)),heldout=list(range(12,16))),rows=rows,scope='Mapping and matched plan preparation only. Native pose/contact verification, full bidirectional reference and actual physics still required; all source failures cannot establish mechanical impossibility.')
    (a.output/'mapping-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(sources=4,coordinate_mapping_passed=True,maximum_slider_error_m=max(r['slider_coordinate_error_m'] for r in rows))))

if __name__=='__main__':main()
