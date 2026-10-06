import datetime,json,hashlib,fcntl,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/flat-table-20261006'
def _write(p,text):
 tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()));tmp.write_text(text,encoding='utf-8');os.replace(str(tmp),str(p))
def record(event,evidence,config=None,updates=None,next_step=None):
 with (D/'.record.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  return _record(event,evidence,config,updates,next_step)
def _record(event,evidence,config=None,updates=None,next_step=None):
 p=D/'STATE.json';s=json.loads(p.read_text()) if p.exists() else dict(local_root=str(R),actor_sha256='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e',flat_table_pickup=False,continuous_pickup_to_extension=False,vision_validated=False,real_robot_ran=False,active_jobs=[])
 s.update(updates or {})
 if next_step:s['next']=next_step
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,evidence=evidence,config=config or {},actor_sha256=s['actor_sha256'],source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'scripts/run_g2_flat_table_demo.py',R/'scripts/run_wuji_flat_connected.py',R/'scripts/prepare_wuji_relaxed_prefix.py',R/'scripts/wuji_prefix_pose_adaptation.py'] if f.exists()},next=s.get('next'));s['last_event']=e;_write(p,json.dumps(s,ensure_ascii=False,indent=2))
 for p in [D/'events.jsonl',Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl')]:
  with p.open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 marker='<!-- WUJI_FLAT_TABLE_HISTORY -->\n';header='# Wuji 完整平放桌面取刀 → 连续推动当前 Goal\n\n先读 `'+str(D/'CONTINUATION.md')+'`。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n\n'+marker
 for p in [R/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),Path('/data/research/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md')]:
  old=p.read_text(encoding='utf-8') if p.exists() else '';_write(p,header+old.split(marker,1)[-1])
 return e
