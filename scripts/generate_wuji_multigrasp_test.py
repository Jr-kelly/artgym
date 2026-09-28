"""Generate a new seed of candidate grasps; selection never uses a learned policy."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import runtime_environment
R=Path(__file__).resolve().parents[1]
def main():
 name='knife_wuji_lowgain_fresh_multigrasp20260928';out=R/'runs/multigrasp-20260928/fresh-generation';out.mkdir(exist_ok=False)
 asset=R/'assets/objects'/name;shutil.copytree(R/'assets/objects/knife_wuji_lowgain_fresh20260922',asset)
 assert hashlib.sha256((asset/'000/mobility.urdf').read_bytes()).hexdigest()=='5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c'
 env=dict(os.environ,PYTHONPATH=str(R),ARTGYM_PROJECTION_CHUNK='128');env.pop('LD_LIBRARY_PATH',None)
 cmd=['/tmp/artgym-lygra-runtime/bin/python','scripts/run_official_seeded.py','--seed','2026092803','func_lygra/generate.py','robot=wuji_artbot','object=knife_wuji_artbot','visualize=False','target_n_result=1000','batch_size_outer=512','batch_size_inner=512','object.asset.input_dir='+str(asset),"object.asset.instance_id='000'",'save_dir='+str(R/'caches/initial_grasp')]
 (out/'spec.json').write_text(json.dumps(dict(seed=2026092803,command=cmd,generation_timeout_seconds=2700,selection='physical criteria only; all candidates and rejections retained',purpose='new test sources, never training or checkpoint selection'),indent=2)+'\n')
 with (out/'generation.log').open('w') as f:subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=2700)
 raw=R/'caches/initial_grasp/wuji_artbot'/name/'000';cache=R/'caches/initial_grasp/wuji'/name/'000';cache.mkdir(parents=True)
 for n in ['qpos.npy','opos.npy']:shutil.copy2(raw/n,cache/n)
 with (out/'validation.log').open('w') as f:subprocess.run([sys.executable,'-m','scripts.validate_fresh_wuji_lowgain','--dataset',name,'--output',str(out/'validation')],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
 print((out/'validation/report.json').read_text())
if __name__=='__main__':main()
