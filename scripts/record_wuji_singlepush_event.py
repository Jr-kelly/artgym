"""Standalone continuation for the updated single-extension goal."""
import datetime,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/singlepush-20261005'
def record(event,evidence,config=None,updates=None,next_step=None):
 s=json.loads((D/'STATE.json').read_text());s.update(updates or {})
 if next_step:s['next']=next_step
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,evidence=evidence,config=config or {},actor_sha256=s['actor_sha256'],next=s['next']);s['last_event']=e;(D/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2))
 for p in [D/'events.jsonl',Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl')]:
  with p.open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 header='# Wuji 单次伸出 >20mm 当前Goal\n\n先读 `'+str(D/'CONTINUATION.md')+'`。旧双循环不再是本轮要求。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n\n<!-- WUJI_SINGLEPUSH_HISTORY -->\n'
 for p in [R/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),Path('/data/research/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md')]:
  old=p.read_text().split('<!-- WUJI_SINGLEPUSH_HISTORY -->\n',1)[-1];p.write_text(header+old)
 return e
