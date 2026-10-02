import json,os,shlex,subprocess
from scripts.record_wuji_press_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']);env=host_tool_environment();root='/tmp/artgym-press-20261002'
subprocess.run(ssh+['mkdir -p '+root+'/source '+root+'/runs'],env=env,check=True)
source=['scripts','isaacgymenvs','rl_games','assets','caches','research/real-knife-press-resistance-20261002','research/multigrasp-20260928/data','research/geometry-generalization-20261002/BASELINE_PHYSICS.json']
subprocess.run(['rsync','-aR','--exclude=__pycache__','--exclude=*.log','-e',shlex.join(ssh[:-1]),*source,'wangjiarui@10.13.160.5:'+root+'/source/'],cwd=R,env=env,check=True)
models=list(json.loads((D/'STATE.json').read_text())['models']);subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*models,'wangjiarui@10.13.160.5:'+root+'/'],cwd=R,env=env,check=True)
jobs=[]
for gpu,(split,take) in enumerate([('pilot',2),('dev',8),('confirm',16)]):
 name='static-'+split+'-repaired';out='runs/real-knife-press-resistance-20261002/static/'+split+'-repaired'
 p=subprocess.Popen(['python3','-m','scripts.wuji_press_jobs','--gpu',str(gpu),'--seconds','180',name,'--','PYTHON','-m','scripts.static_wuji_press','--label','real','--split',split+'-repaired-attempts','--take',str(take),'--output',out],cwd=R);jobs.append((p,name,out))
for p,name,out in jobs:assert p.wait()==0,name
subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*['wangjiarui@10.13.160.5:'+root+'/./'+out for _,_,out in jobs],str(R)+'/'],env=env,check=True)
record('small_fresh_static_cohorts_completed',evidence='runs/real-knife-press-resistance-20261002/static/dev-repaired/report.json',next='Inspect coverage and runzero-load operability/independentpress pilot; no policy-filtering')
