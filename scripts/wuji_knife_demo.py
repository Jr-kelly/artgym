"""Reproduce the verified Wuji knife demo from the checked-in reference motion.

Run inside the artgym Conda environment, from the repository root.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from scripts.build_wuji_knife_demo import build_asset
from scripts.wuji_kinematics import ROOT, WujiKinematics


def prepare(output, cycles=1, preset_path=None):
    preset_path = preset_path or ROOT/'assets/demo/wuji_knife/fingertip_preset.yaml'
    preset=yaml.safe_load(Path(preset_path).read_text())
    hand=WujiKinematics()
    digest=hashlib.sha256((ROOT/hand.config['asset']).read_bytes()).hexdigest()
    if digest!=preset['hand_urdf_sha256'] or hand.names!=preset['dof_names']:
        raise ValueError('Reference motion belongs to a different Wuji hand asset; regenerate the grasp/motion')
    if cycles<1:
        raise ValueError('cycles must be positive')
    if 'asset' in preset:
        asset = ROOT/preset['asset']
        if hashlib.sha256(asset.read_bytes()).hexdigest() != preset['asset_sha256']:
            raise ValueError('Knife asset differs from the reference trajectory; regenerate it')
    else:
        build_asset(ROOT/'assets/objects/knife_wuji_demo/000',**preset['dimensions_m'])
    output.mkdir(parents=True,exist_ok=True)
    initial=preset['initial']
    np.savez(output/'initial.npz',**{k:np.asarray([v]) for k,v in initial.items()})
    if 'joint_waypoints_rad' in preset:
        waypoints=np.asarray(preset['joint_waypoints_rad'])
        q=waypoints[:,1:].copy()
    else:
        waypoints=np.asarray(preset['thumb_waypoints_rad'])
        q=np.tile(initial['targets'],(len(waypoints),1));q[:,-4:]=waypoints[:,1:]
    if np.any(q<hand.lower-1e-6) or np.any(q>hand.upper+1e-6):
        raise ValueError('Reference motion exceeds hand joint limits')
    times,paths=[],[]
    for cycle in range(cycles):
        path=q.copy()
        if cycle:
            # Continue from the previous endpoint without resetting any state.
            mask=waypoints[:,0]<=1
            fraction=(1-np.cos(np.pi*waypoints[mask,0]))/2
            path[mask]=q[-1]*(1-fraction[:,None])+q[mask]*fraction[:,None]
        keep=slice(None) if cycle==0 else slice(1,None)
        times.extend((waypoints[keep,0]+12*cycle).tolist())
        paths.extend(path[keep].tolist())
    np.savez(output/'trajectory.npz',time=times,qpos=paths)
    return preset


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'tmp/wuji-knife-demo')
    p.add_argument('--cycles',type=int,default=1)
    p.add_argument('--no-render',action='store_true')
    p.add_argument('--gpu-pipeline',action='store_true')
    p.add_argument('--preset',type=Path,default=ROOT/'assets/demo/wuji_knife/fingertip_preset.yaml')
    args=p.parse_args()
    preset=prepare(args.output,args.cycles,args.preset)
    from scripts.run_wuji_knife_demo import main as simulate
    sim_args=['--candidates',str(args.output/'initial.npz'),'--trajectory',str(args.output/'trajectory.npz'),
              '--seconds',str(args.cycles*12),'--output',str(args.output)]
    if 'asset' in preset: sim_args.extend(['--asset',preset['asset']])
    for key in ('friction', 'damping', 'dimension_label'):
        if key in preset.get('simulation', {}):
            sim_args.extend(['--'+key.replace('_','-'),str(preset['simulation'][key])])
    if preset.get('simulation', {}).get('filtered_self_collisions'):
        sim_args.append('--filtered-self-collisions')
    if preset.get('simulation', {}).get('require_fingertip_grip'):
        sim_args.append('--require-fingertip-grip')
    for key in ('camera_position', 'camera_target'):
        if key in preset.get('simulation', {}):
            sim_args.extend(['--'+key.replace('_','-')]+list(map(str,preset['simulation'][key])))
    if not args.no_render:sim_args.append('--render')
    if args.gpu_pipeline:sim_args.append('--gpu-pipeline')
    simulate(sim_args)
    plot_result(args.output)
    result=json.loads((args.output/'report.json').read_text())['ranked'][0]
    if not result['all_cycles_pass'] or result['max_joint_limit_violation_rad']>.05:
        raise RuntimeError(f'Demo did not meet motion/stability criteria; see {args.output}/report.json')
    print('WUJI KNIFE DEMO PASSED:',args.output)


def plot_result(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.spatial.transform import Rotation
    state=np.load(output/'rollout.npz')['states'][:,0]
    initial=np.load(output/'initial.npz')
    center=Rotation.from_quat([.5,-.5,.5,.5]).apply(initial['centers'][0])+[0,0,.5]
    time=state[:,0]
    fig,axes=plt.subplots(2,1,figsize=(10,5),sharex=True,constrained_layout=True)
    axes[0].plot(time,state[:,-1]*1000,color='#dd8500',label='Measured slider')
    axes[0].step(time,np.where(time%12<6,40,0),where='post',color='#777777',linestyle='--',label='Goal')
    axes[0].set(ylabel='Slider (mm)',ylim=(-2,44),title='Wuji utility knife: scripted hand commands, passive slider')
    axes[0].legend(loc='upper right')
    axes[1].plot(time,np.linalg.norm(state[:,1:4]-center,axis=1)*1000,color='#2376b7')
    axes[1].set(ylabel='Handle drift (mm)',xlabel='Time (s)',ylim=(0,15))
    for ax in axes:ax.grid(alpha=.2)
    fig.savefig(output/'metrics.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
