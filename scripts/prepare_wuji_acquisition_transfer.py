"""Add a physically acquired grasp to dense geometry caches without policy filtering.

Caches are static manipulation proxies (zero initial velocity), explicitly
separate from the continuous G2 trajectory, whose state and velocity are retained.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.prepare_wuji_geometry import adapt
from scripts.prepare_wuji_command_states import states_for_seed
from scripts.record_wuji_robust_goal import record
R=Path(__file__).resolve().parents[1];D=R/'research/robust-knife-family-20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--time',type=float,default=15.);p.add_argument('--name',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-family',default='knife_wuji_dense_acquired_20261003');p.add_argument('--seed',type=int,default=2026100341);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);family=R/'assets/objects'/a.name;family.mkdir(exist_ok=False);z=np.load(a.trace);i=int(np.argmin(abs(z['time']-a.time)));hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    wrist=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);obj=np.linalg.inv(wrist)@transform(z['object'][i,:3],z['object'][i,3:7]);meta=json.loads((R/'assets/objects/knife_wuji_real_size_20261002/000/parameters.json').read_text());slider=obj@transform(np.array(meta['slider_origin'])+[0,0,z['slider'][i]])
    def pose(t):return np.r_[t[:3,3],Rotation.from_matrix(t[:3,:3]).as_quat()]
    ids=json.loads((a.trace.parent/'physics.json').read_text())['hand_indices'];q=z['q'][i];targets=z['target'][i,ids];tips=np.concatenate([hand.forward(q)[n][:3,3] for n in hand.config['track_links']]);seed=np.r_[q,targets,pose(obj),pose(slider),z['slider'][i],tips,np.zeros(5)].astype(np.float32)
    assert seed.shape==(75,) and abs(float(z['slider'][i])-meta['joint_lower'])<.001
    assert z['object'][i,2]>.80, 'Actual source must be lifted'
    np.save(a.output/'closed-acquired-seed.npy',seed)
    source_record=dict(trace=str(a.trace),trace_sha256=sha(a.trace),time_s=float(z['time'][i]),wrist_quaternion_xyzw=z['wrist'][i,3:7].tolist(),object_velocity=z['object'][i,7:].tolist(),slider_velocity=float(z['slider_velocity'][i]),thumb_slider_contacts=int(z['finger_slider_contacts'][i,0]),body_contacts=z['finger_body_contacts'][i].tolist(),source_selection='Pre-policy fixed15s acquisition frame, selected for lifted closed functional grasp, no policy performance filtering',scope='Actual simulated acquisition; static training proxy zeroes velocities, continuous episode never does')
    (a.output/'wrist.json').write_text(json.dumps(source_record,indent=2));record('dense_acquisition_transfer_started',config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},evidence=[str(a.output/'wrist.json')],next='Adapt actual grasp to all512 existing train shapes and4 independent shapes; retain old sources50%, count all initialization failures')
    original=R/'assets/objects'/a.source_family;entries=[];lbx=json.loads((original/'lbx.json').read_text())
    for index,sid in enumerate(lbx):
        shutil.copytree(original/sid,family/sid);params=json.loads((family/sid/'parameters.json').read_text());size=np.array(params['handle_size']);origin=np.array(params['slider_origin']);out,diag=adapt(hand,seed,size,origin,np.array(meta['handle_size']));rot=Rotation.from_quat(out[43:47]);offset=origin-np.array(meta['slider_origin']);offset[1]-=(size[1]-.012)/2
        point=hand.contacts(out[:20])[0][0];adjusted,error=hand.solve_finger('thumb',point+rot.apply(offset),out[:20]);delta=adjusted-out[:20];out[:20]=adjusted;out[20:40]=np.clip(out[20:40]+delta,hand.lower,hand.upper);out[47:50]=out[40:43]+rot.apply(origin+[0,0,out[54]]);out[55:70]=np.concatenate([hand.forward(adjusted)[n][:3,3] for n in hand.config['track_links']])
        old=R/'caches/initial_grasp/wuji'/a.source_family/sid;cache=R/'caches/initial_grasp/wuji'/a.name/sid;cache.mkdir(parents=True);shutil.copy2(old/'grasp_state_metadata.json',cache/'grasp_state_metadata.json');pools={}
        for split,extra in [('train',0),('test',1)]:
            prior=np.load(old/split/'valid_grasps.npy');new=states_for_seed(out[None],a.seed*10000+index*2+extra,hand,len(prior));pool=np.r_[prior,new];path=cache/split/'valid_grasps.npy';path.parent.mkdir();np.save(path,pool);pools[split]=dict(n=len(pool),sha256=sha(path),path=str(path.relative_to(R)))
        entries.append(dict(instance=sid,split='heldout' if sid in ['012','013','014','015'] else 'train',urdf_sha256=sha(family/sid/'mobility.urdf'),adaptation=dict(thumb_offset_ik_error_m=error,**diag),pools=pools))
        if index%64==0:print(json.dumps(dict(adapted=index+1,total=len(lbx))),flush=True)
    (family/'lbx.json').write_text(json.dumps(lbx));config=R/'isaacgymenvs/cfg/object'/(a.name+'.yaml');config.write_text('defaults:\n  - '+a.source_family+'\n  - _self_\nasset:\n  asset_root: assets/objects/'+a.name+'\n')
    manifest=dict(args=vars(a),source=source_record,source_seed_sha256=sha(a.output/'closed-acquired-seed.npy'),entries=entries,source_mix='50% new actual longside acquisition;25% previous actual negative-end acquisition;25% four original functional sources',selection='No policy filter, unchanged independent geometry definitions, all initialization failures counted',scope='Static manipulation training proxy, not full demo or velocity-faithful handover',source_geometry_manifest_sha256=sha(D/'dense-family-v1/manifest.json'))
    (a.output/'manifest.json').write_text(json.dumps(manifest,default=str,indent=2));record('dense_acquisition_transfer_finished',evidence=[str(a.output/'manifest.json'),str(config.relative_to(R))],manifest_sha256=sha(a.output/'manifest.json'),next='Train and check actual pressure-location and body-support improvement on same legal actor; reconnect continuous G2')
if __name__=='__main__':main()
