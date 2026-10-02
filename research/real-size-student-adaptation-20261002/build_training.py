import json,shutil
import numpy as np
from scripts.record_wuji_real_size_goal import R,D,record
from scripts.wuji_width_contract import sha,real_size_slots
name='knife_wuji_real_size_train_20261002';out=R/'assets/objects'/name;out.mkdir();cache=R/'caches/initial_grasp/wuji'/name;cache.mkdir(parents=True);lbx={}
for i,obj in enumerate(['knife_wuji_bridge3_20260922','knife_wuji_real_size_20261002','knife_wuji_bridge3_20260922']):
 instance='%03d'%i;shutil.copytree(R/'assets/objects'/obj/'000',out/instance);shutil.copytree(R/'caches/initial_grasp/wuji'/obj/'000',cache/instance);lbx[instance]=json.loads((R/'assets/objects'/obj/'lbx.json').read_text())['000']
(out/'lbx.json').write_text(json.dumps(lbx));cfg=R/'isaacgymenvs/cfg/object'/(name+'.yaml');cfg.write_text('defaults:\n  - knife_wuji_bridge3_20260922\n  - _self_\nasset:\n  asset_root: assets/objects/'+name+"\n  instance_id_list: ['000', '001', '002']\n")
asset_files={str(p.relative_to(R)):sha(p) for p in out.rglob('*') if p.is_file()};asset_files[str(cfg.relative_to(R))]=sha(cfg)
for arm in ['C','G']:
 pools=[]
 for group,source in [(0,i) for i in range(4)]+[(1,3)]:
  real=group==1 and arm=='G';p=R/('runs/real-size-student-adaptation-20261002/static/train/valid-states.npy' if real else 'research/width-student-distillation-20261002/data/baseline/train-valid-source%d.npy'%source)
  pools.append(dict(group=group,source=source,geometry='real' if real else 'baseline',states=str(p.relative_to(R)),sha256=sha(p),n=len(np.load(p))))
 (D/(arm+'-training.json')).write_text(json.dumps(dict(round='real-size-student-adaptation-20261002',arm=arm,statically_validated=True,slots=real_size_slots(arm),pools=pools,asset_files=asset_files),indent=2))
record('paired_training_distribution_registered',target_slots=192,anchor_slots_each_source=16,arms='C original baseline, G labeled R in reports replaces target source3 with real-sized knife',updates_each=800,start=54400,end=55200,save_at=[54800,55200],teacher_mixing=0,next='Use only after fresh dev shows usable teacher trajectories; equal parent Adam/RNG, no tuning')
