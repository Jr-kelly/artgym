"""Append evidence and refresh all current handoff entry points."""
import datetime,json,argparse,fcntl
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/artmanip-recovery-20260930'
def _record(event, **details):
    row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,**details)
    for p in [D/'DECISIONS.jsonl',R.parent/'runs/wuji-goal/journal/events.jsonl']:
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    state=json.loads((D/'STATE.json').read_text()); state['last_event']=row
    (D/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    text='# 当前 ArtManip recovery Goal\n\n工作区 '+str(R)+'\n\n先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。\n\n最近事件：\n```json\n'+json.dumps(row,ensure_ascii=False,indent=2)+'\n```\n\n预算与任务状态：\n```json\n'+json.dumps(state,ensure_ascii=False,indent=2)+'\n```\n'
    for p in [D/'HANDOFF.md',R/'WUJI_GOAL_HANDOFF.md']:
        p.write_text(text)
    for p in [R.parent/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
        if p.exists():
            old=p.read_text(); marker='<!-- RECOVERY_HISTORY -->'
            if marker in old:old=old.split(marker,1)[1].lstrip('\n')
            p.write_text(text+'\n'+marker+'\n'+old)
    return row
def record(event, **details):
    with (D/'.event.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _record(event,**details)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('event');p.add_argument('details');a=p.parse_args();print(json.dumps(record(a.event,**json.loads(a.details)),ensure_ascii=False))
