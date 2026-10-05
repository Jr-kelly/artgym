"""Persistent newknife state, journal, and resumable handoff. No robot interface."""
import json,datetime,argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/newknife-20261005'
def record(event,evidence,config=None,next_step=None,updates=None):
 s=json.loads((D/'STATE.json').read_text());s.update(updates or {})
 if next_step:s['next']=next_step
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,evidence=evidence,config=config or {},actor_sha256=s['actor_sha256'],next=s['next']);s['last_event']=e
 (D/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 for p in [D/'events.jsonl',Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl')]:
  with p.open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 header='# Wuji 新刀连续伸缩当前轮\n\n实际副本 `'+str(R)+'`。先读 research/newknife-20261005/STATE.json。旧结果保留；新命令35mm；禁止子代理和真机动作。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n\n<!-- WUJI_NEWKNIFE_HISTORY -->\n'
 for p in [R/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),Path('/data/research/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md')]:
  old=p.read_text();old=old.split('<!-- WUJI_NEWKNIFE_HISTORY -->\n',1)[-1];p.write_text(header+old)
 return e
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('event');p.add_argument('--evidence',default='');p.add_argument('--next');a=p.parse_args();print(json.dumps(record(a.event,a.evidence,next_step=a.next),ensure_ascii=False))
