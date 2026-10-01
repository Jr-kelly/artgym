"""Current geometry round ledger; previous round files are immutable."""
import datetime, fcntl, json, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'research/geometry-generalization-20261002'
def record(event, **details):
 with (D/'.event.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,**details)
  for p in [D/'DECISIONS.jsonl',R.parent/'runs/wuji-goal/journal/events.jsonl']:
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
  s=json.loads((D/'STATE.json').read_text());s.update(details.get('state_updates',{}));s['last_event']=row
  for key in ['phase','next']:
   if key in details:s[key]=details[key]
  jobs=R/'runs/geometry-generalization-20261002/jobs'
  s['active_jobs']=[json.loads(p.read_text()) for p in jobs.glob('*/identity.json') if not (p.parent/'result.json').exists()]
  s['new_gpu_hours']=sum(json.loads(p.read_text())['gpu_hours'] for p in jobs.glob('*/result.json'))
  s['cumulative_gpu_hours']=s['historical_gpu_hours']+s['new_gpu_hours'];s['remaining_gpu_hours']=s['max_gpu_hours']-s['cumulative_gpu_hours']
  current=datetime.datetime.now(datetime.timezone.utc);s['active_gpu_elapsed_hours']=sum(max(0,(current-datetime.datetime.fromisoformat(j['start_utc'])).total_seconds())/3600 for j in s['active_jobs'])
  s['cumulative_gpu_hours_including_active']=s['cumulative_gpu_hours']+s['active_gpu_elapsed_hours'];s['remaining_including_active']=s['max_gpu_hours']-s['cumulative_gpu_hours_including_active']
  (D/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
  message='# 当前 Wuji 尺寸泛化 Goal\n\n工作区 `'+str(R)+'`。先读 research/geometry-generalization-20261002/{GOAL.md,STATE.json,HANDOFF.md,PENDING_TASKS.md,DECISIONS.jsonl}。禁止子代理；旧最终集保持关闭。PID/利用率为带时间历史记录，须重新验证。旧墙钟截止及续训方案已由新Goal替换。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n'
  (D/'HANDOFF.md').write_text(message);(R/'WUJI_GOAL_HANDOFF.md').write_text(message)
  marker='<!-- GEOMETRY_HISTORY -->'
  for p in [R.parent/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
   old=p.read_text() if p.exists() else ''
   if marker in old:old=old.split(marker,1)[1].lstrip('\n')
   p.write_text(message+'\n'+marker+'\n'+old)
  if not s.get('remote_mirror_disabled'):
   from scripts.host_tool_environment import host_tool_environment
   destination='wangjiarui@10.13.160.5:/tmp/artgym-geometry-20261002/'
   commands=[['rsync','-az','-e','ssh -p33024',str(D/'STATE.json'),str(D/'GOAL.md'),str(D/'HANDOFF.md'),str(D/'DECISIONS.jsonl'),*([str(D/'PENDING_TASKS.md')] if (D/'PENDING_TASKS.md').exists() else []),destination+'research/geometry-generalization-20261002/'],['rsync','-az','-e','ssh -p33024',str(R/'WUJI_GOAL_HANDOFF.md'),destination],['rsync','-az','-e','ssh -p33024',str(R.parent/'runs/wuji-goal/journal/events.jsonl'),destination+'runs/wuji-goal/journal/']]
   try:
    for command in commands:subprocess.run(command,check=True,capture_output=True,timeout=15,env=host_tool_environment())
   except (subprocess.SubprocessError,OSError) as error:
    # Mirror failure never launches/restarts compute. Disable automatic writes
    # until explicitly reviewed; local durable journal remains authoritative.
    s['remote_mirror_disabled']=True;s['remote_mirror_error']=str(error)
    (D/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
  return row
