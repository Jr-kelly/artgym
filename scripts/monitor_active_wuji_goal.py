"""Record host health and current learning progress without launching compute."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]
REMOTE=r'''from pathlib import Path
import json,os,subprocess,datetime
r=Path('/home/wangjiarui/artgym-experiments-20260921')
def read(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}
host=os.uname().nodename
eight=host=='d-20260921021501-6zzgt'
names=['sharpa_reward_upstream_recover3400_20260923_v2'] if eight else ['sharpa_reward_corrected_recover1500_exclusive_v1']
if eight:
 names+=['wuji-goal/diagnostics/command-dagger-'+a+'-1504-v3' for a in ['absolute','incremental']]
registry=read(r/'goal_health_monitor.json')
names=registry.get('hosts',{}).get(host,{}).get('runs',names)
results={}
for name in names:
 p=r/'runs'/name;s=read(p/'status.json') or read(p/'pipeline-status.json')
 launch=read(p/'launcher.json');training=read(p/'training/status.json') or read(p/'fitting/status.json')
 stages=[{k:v for k,v in stage.items() if k in ['name','status','pid','returncode','gpu']} for stage in s.get('stages',[])]
 for stage in stages:
  pid=stage.get('pid');proc=Path('/proc')/str(pid)
  stage['pid_exists_on_this_host']=proc.exists() if pid else False
  if stage['pid_exists_on_this_host']:
   try:stage['actual_cmdline']=proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   except OSError:pass
 reports=[]
 for f in p.glob('formal-*/report.json'):
  d=read(f);records=d.get('records',[])
  reports.append(dict(name=f.parent.name,training300=sum(x['stable_full_all_endpoints'] for x in records[:300]),fourth32=sum(x['stable_full_all_endpoints'] for x in records[300:]),source='reported; awaiting independent raw trace rescore'))
 results[name]=dict(status=s.get('status'),error=s.get('error'),launcher=launch.get('pid'),stages=stages,checkpoint=read(p/'checkpoints/latest.json'),training={k:v for k,v in training.items() if k in ['status','updates_completed','updates_budget','checks','latest_loss','heartbeat']},reports=reports)
u=read(r/('runs/gpu-utilization/status.json' if eight else 'runs/gpu-utilization-four/status.json'))
print(json.dumps(dict(host=host,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runs=results,utilization=u,gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True))))
'''


def query(host,port):
    args=['ssh','-p',str(port),'-i','/home/agiuser/.ssh/id_ed25519_h200',
          '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10',
          'wangjiarui@'+host,'python3 -']
    try:
        result=subprocess.run(args,input=REMOTE,text=True,capture_output=True,timeout=35)
        if result.returncode: return dict(access='failed',error=result.stderr,returncode=result.returncode)
        return dict(access='connected',**json.loads(result.stdout))
    except Exception as error:return dict(access='failed',error=repr(error))


def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');args=p.parse_args()
    out=ROOT/'runs/wuji-goal/health';out.mkdir(exist_ok=True)
    lock=(out/'monitor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    while True:
        with ThreadPoolExecutor(max_workers=2) as pool:
            four=pool.submit(query,'10.14.0.73',30296);eight=pool.submit(query,'10.14.0.106',30147)
            state=dict(observed_utc=now(),four=four.result(),eight=eight.result())
        local=Path('/proc/88339/cmdline')
        state['original_local_training']=dict(pid=88339,alive=local.exists(),
            cmdline=local.read_bytes().replace(b'\0',b' ').decode() if local.exists() else None)
        registry=json.loads((ROOT/'goal_health_monitor.json').read_text()) if (ROOT/'goal_health_monitor.json').exists() else {}
        state['local_runs']={}
        for name in registry.get('local_runs',[]):
            folder=ROOT/name
            entry={}
            for filename in ['status.json','collection-status.json','failure.json']:
                path=folder/filename
                if path.exists():
                    data=json.loads(path.read_text());entry[filename]={k:v for k,v in data.items() if k in ['status','step','frames','images','error','finished','heartbeat']}
                    if data.get('stages'):
                        entry['stages_completed']=sum(v.get('status')=='completed' for v in data['stages'])
                        declared=data.get('spec',{}).get('stages')
                        entry['stages_expected']=len(declared) if declared is not None else None
                        latest=data['stages'][-1]
                        entry['latest_stage']={k:latest.get(k) for k in ['name','status','pid','returncode']}
                        stage_name=latest.get('name',str(latest.get('seconds','')))
                        child_status=folder/stage_name/'status.json'
                        if child_status.exists():
                            child=json.loads(child_status.read_text())
                            entry['latest_stage'].update({k:child[k] for k in ['step','heartbeat','checks'] if k in child})
            state['local_runs'][name]=entry
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        atomic_json(out/(stamp+'.json'),state);atomic_json(out/'status.json',state)
        lines=['# Wuji 运行健康记录','',state['observed_utc'],
               '', '每5分钟只读检查；106与93为同一八卡入口。这里的成功数来自运行报告，完整trace独立重算仍由实验总结完成。','']
        for name in ['four','eight']:
            h=state[name];lines+=['## '+name,'',h['access']]
            if h['access']!='connected':lines+=['',str(h.get('error'))];continue
            lines+=['',h['host']+'; boot '+h['boot_id'],'']
            for sec,w in h['utilization'].get('windows',{}).items():
                lines.append(f"- GPU {sec}s窗口: {w['mean_percent']:.2f}%，实际覆盖{w['covered_seconds']:.0f}s")
            lines+=['','利用率告警：'+str(h['utilization'].get('alert')),'']
            for run,d in h['runs'].items():
                lines+=['- '+run+': '+str(d['status'])+', CP='+str(d['checkpoint'].get('epoch'))+', student更新='+str(d['training'].get('updates_completed'))]
                if d['error']:lines+=['  '+str(d['error'])]
            lines+=['','```text',h['gpu'].rstrip(),'```','']
        lines+=['## Local collections','',json.dumps(state['local_runs'],ensure_ascii=False,indent=2),'']
        (out/'LATEST.md').write_text('\n'.join(lines)+'\n')
        with (ROOT/'runs/wuji-goal/journal/events.jsonl').open('a') as f:
            f.write(json.dumps(dict(kind='health_check',recorded_utc=now(),evidence=str((out/(stamp+'.json')).relative_to(ROOT)),access={k:state[k]['access'] for k in ['four','eight']}))+'\n')
        print(json.dumps(dict(time=now(),snapshot=str(out/(stamp+'.json')))),flush=True)
        if args.once:break
        time.sleep(300)


if __name__=='__main__':main()
