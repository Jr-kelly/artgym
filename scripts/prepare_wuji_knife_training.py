"""Generate knife grasp candidates and validate them through ArtGym's ArtGrasp."""
import argparse
import itertools
import os
import subprocess
import sys

import numpy as np
import yaml

from scripts.wuji_kinematics import ROOT, WujiKinematics
from scripts.wuji_knife_demo import prepare


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates-only',action='store_true')
    args=p.parse_args()
    os.chdir(ROOT)
    # These historical seeds belong to the original thick demo object.
    prepare(ROOT/'tmp/knife-training-input', preset_path=ROOT/'assets/demo/wuji_knife/preset.yaml')
    hand=WujiKinematics()
    seeds=yaml.safe_load((ROOT/'assets/demo/wuji_knife/grasp_seeds.yaml').read_text())['seeds']
    qs,poses=[],[]
    for seed in seeds:
        for a,b,c in itertools.product((-.1,0,.1),(-.15,0,.15),(-.15,0,.15)):
            q=np.asarray(seed['qpos'],dtype=np.float32)
            q[-4]+=a;q[-2]+=b;q[-1]+=c
            qs.append(np.clip(q,hand.lower,hand.upper));poses.append(seed['object_transform'])
    while len(qs)%64:
        qs.append(qs[0]);poses.append(poses[0])
    path=ROOT/'caches/initial_grasp/wuji/knife_wuji_demo/000'
    path.mkdir(parents=True,exist_ok=True)
    np.save(path/'qpos.npy',qs);np.save(path/'opos.npy',np.asarray(poses,dtype=np.float32))
    print('Generated',len(qs),'raw candidates at',path,flush=True)
    if args.candidates_only:return
    subprocess.run([sys.executable,'-m','isaacgymenvs.valid_grasp','--hand','wuji','--object','knife_wuji_demo',
                    '--instance-id','000','--pipeline','cpu','--num-envs',str(len(qs)),
                    '--episode-length','120','--pos-threshold','.01','--rot-threshold','.2',
                    '--headless','--override','task.env.forceScale=0'],check=True)
    valid=np.load(path/'valid_grasps.npy')
    if valid.ndim!=2 or valid.shape[1]!=75 or not len(valid) or not np.isfinite(valid).all():
        raise RuntimeError('No usable full-state grasp cache was produced')
    print('WUJI KNIFE GRASP VALIDATION PASSED:',valid.shape)


if __name__=='__main__':
    main()
