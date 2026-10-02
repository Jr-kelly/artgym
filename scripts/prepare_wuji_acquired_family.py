"""Static manipulation proxy caches derived from an actually simulated pickup.

This never resets the continuous demo. Cache initialization zeroes velocities and
is explicitly a manipulation-training proxy, not evidence of continuous success.
All source grasps and all geometry adaptations remain, without policy filtering.
"""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.prepare_wuji_geometry import adapt
from scripts.prepare_wuji_command_states import states_for_seed
R=Path(__file__).resolve().parents[1]
D=R/'research/robust-knife-family-20261003'
NAME='knife_wuji_acquired_family_20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    output=D/'acquired-family-v1';output.mkdir(exist_ok=False)
    trace_path=R/'runs/robust-knife-family-20261003/demo/g2-functional-equilibrium-v11/trace.npz'
    # Use the measured closed state BEFORE R800. No post-hoc policy success selection.
    if not trace_path.exists():
        matches=list((R/'runs/robust-knife-family-20261003/demo').glob('*v11/trace.npz'))
        assert len(matches)==1;trace_path=matches[0]
    z=np.load(trace_path);i=int(np.argmin(abs(z['time']-15.)))
    hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    wrist=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);obj=np.linalg.inv(wrist)@transform(z['object'][i,:3],z['object'][i,3:7])
    nominal=json.loads((R/'assets/objects/knife_wuji_real_size_20261002/000/parameters.json').read_text())
    slider=obj@transform(np.array(nominal['slider_origin'])+[0,0,z['slider'][i]])
    def pose(t):return np.r_[t[:3,3],Rotation.from_matrix(t[:3,:3]).as_quat()]
    names=json.loads((trace_path.parent/'physics.json').read_text())['hand_indices']
    q=z['q'][i];target=z['target'][i,names]
    tips=np.concatenate([hand.forward(q)[n][:3,3] for n in hand.config['track_links']])
    acquired=np.r_[q,target,pose(obj),pose(slider),z['slider'][i],tips,np.zeros(5)].astype(np.float32)
    assert acquired.shape==(75,)
    assert abs(float(z['slider'][i])-nominal['joint_lower'])<.001
    np.save(output/'closed-acquired-seed.npy',acquired)
    wrist_record=dict(wrist_quaternion_xyzw=z['wrist'][i,3:7].tolist(),source=str(trace_path.relative_to(R)),trace_sha256=sha(trace_path),time_s=float(z['time'][i]),object_velocity=z['object'][i,7:].tolist(),slider_from_lower_m=float(z['slider'][i]-nominal['joint_lower']),scope='Measured simulated functional acquisition; no hardware evidence; training cache zeroes velocity, continuous runner does not')
    (output/'wrist.json').write_text(json.dumps(wrist_record,indent=2))
    source=R/'assets/objects/knife_wuji_robust_family_20261003';family=R/'assets/objects'/NAME;shutil.copytree(source,family)
    seeds=np.load(R/'research/real-size-student-adaptation-20261002/data/real/adapted-seeds.npy')
    allseeds=np.r_[seeds,acquired[None]];entries=[]
    for i in range(16):
        sid=f'{i:03d}';meta=json.loads((family/sid/'parameters.json').read_text());size=np.array(meta['handle_size']);origin=np.array(meta['slider_origin']);slider_size=np.array(meta['slider_size'])
        offsets=origin-np.array(nominal['slider_origin']);offsets[1]-=(size[1]-.012)/2
        adapted=[];reports=[]
        for j,s in enumerate(allseeds):
            out,report=adapt(hand,s,size,origin,np.array(nominal['handle_size']))
            rotation=Rotation.from_quat(out[43:47]);out[47:50]=out[40:43]+rotation.apply(origin+[0,0,out[54]])
            point=hand.contacts(out[:20])[0][0]
            # Geometry, slider center and height jointly shift the thumb target.
            shift=rotation.apply(offsets+[0,(slider_size[1]-.003)/2,0])
            adjusted,err=hand.solve_finger('thumb',point+shift,out[:20]);delta=adjusted-out[:20]
            out[:20]=adjusted;out[20:40]=np.clip(out[20:40]+delta,hand.lower,hand.upper)
            out[55:70]=np.concatenate([hand.forward(adjusted)[n][:3,3] for n in hand.config['track_links']])
            adapted.append(out);reports.append(dict(source=j,kind='original functional' if j<4 else 'actual closed acquisition',thumb_ik_error_m=err,**report))
        np.save(output/f'adapted-{sid}.npy',adapted)
        cache=R/'caches/initial_grasp/wuji'/NAME/sid;cache.mkdir(parents=True)
        shutil.copy2(R/'caches/initial_grasp/wuji/knife_wuji_robust_family_20261003'/sid/'grasp_state_metadata.json',cache/'grasp_state_metadata.json')
        pools={}
        for split,n,seed in [('train',12,2026100320),('test',8,2026100321)]:
            # 50% actual acquired source, 50% four original functional sources.
            pool=np.concatenate([states_for_seed(np.array(s)[None],seed*1000+i*10+j,hand,n*(4 if j==4 else 1)) for j,s in enumerate(adapted)])
            path=cache/split/'valid_grasps.npy';path.parent.mkdir();np.save(path,pool)
            pools[split]=dict(n=len(pool),path=str(path.relative_to(R)),sha256=sha(path))
        entries.append(dict(instance=sid,split='train' if i<12 else 'heldout',adaptation=reports,pools=pools))
    config=R/'isaacgymenvs/cfg/object'/(NAME+'.yaml')
    config.write_text('defaults:\n  - knife_wuji_robust_family_20261003\n  - _self_\nasset:\n  asset_root: assets/objects/'+NAME+'\n')
    manifest=dict(name=NAME,source=wrist_record,source_seed_sha256=sha(output/'closed-acquired-seed.npy'),geometry_source_manifest_sha256=sha(D/'family-manifest.json'),entries=entries,selection='All four old functional sources plus actual closed source; no policy filtering; all initialization failures counted',scope='Static presetheld manipulation proxy; actual50-frame hold before actor; continuous acquisition must be tested separately')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(dict(name=NAME,manifest_sha256=sha(output/'manifest.json'),closed_acquired_slider_m=float(acquired[54]))))
if __name__=='__main__':main()
