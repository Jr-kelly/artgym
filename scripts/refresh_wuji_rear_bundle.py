"""Freeze deployment v8 around unchanged weights/reference and reviewed entry code."""
import json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'research/rear-sim2real-20261009';s=json.loads((d/'bundle-deploy-v7.json').read_text());names=set(s['required_sha256'])
 # Freeze framework sources copied from base as well as model resources: hashes
 # must cover imported task/player/rl_games code, not only configurations.
 for namespace in ['isaacgymenvs','rl_games']:
  names.update(str(p.relative_to(ROOT)) for p in (ROOT/namespace).rglob('*.py') if '__pycache__' not in p.parts and '.git' not in p.parts)
 names.update(['scripts/wuji_rear_session.py','scripts/wuji_rear_field.py','scripts/g2_local_python.sh','scripts/restore_wuji_rear_deployment.py'])
 names.discard('scripts/restore_wuji_rear_deployment.py') if not (ROOT/'scripts/restore_wuji_rear_deployment.py').is_file() else None
 names.update(['scripts/wuji_rear_profiles.py','scripts/wuji_rear_sdk_backend.py','scripts/wuji_rear_sdk_worker.py'])
 s['required_sha256']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}
 import yaml
 s['hand_model_urdf']=yaml.safe_load((ROOT/'isaacgymenvs/cfg/hand/wuji.yaml').read_text())['asset']
 log=ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/commands.jsonl';rows=[json.loads(l) for l in log.read_text().splitlines()];reserve=s['issued_limit_reserve_rad']
 lo=np.asarray(s['model_lower_rad'])+reserve;hi=np.asarray(s['model_upper_rad'])-reserve
 u=np.array([r['issued_target_rad'] for r in rows]+[np.clip(s['open_q_rad'],lo,hi).tolist(),np.clip(s['hold_target_rad'],lo,hi).tolist()])
 s['deployment_required_target_envelope']=dict(lower_rad=u.min(0).tolist(),upper_rad=u.max(0).tolist(),maximum_issued_speed_rad_s=(np.max(abs(np.diff(np.array([r['issued_target_rad'] for r in rows]),axis=0)),axis=0)*30).tolist(),source=str(log.relative_to(ROOT)),source_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),scope='Actually-issued nominal full task plus reserved open/hold; not universal pose bounds')
 s['g2_hardware_status']='blocked_no_exact_model_matched_sdk';s['deployment_revision']='v3-hardware-chain-audit'
 out=d/'bundle-deploy-v8.json';out.write_text(json.dumps(s,indent=2)+'\n');print(hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=='__main__':main()
