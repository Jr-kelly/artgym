"""Current round ledger; old frozen experiments are never updated."""
import datetime, fcntl, json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
D = R / 'research/support-pressure-20261003'
def record(event, **details):
    with (D / '.event.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        row = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=event, **details)
        for p in [D/'events.jsonl', R.parent/'runs/wuji-goal/journal/events.jsonl']:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a') as f: f.write(json.dumps(row, ensure_ascii=False)+'\n')
        state=json.loads((D/'STATE.json').read_text()); state.update(details.get('state_updates', {})); state['last_event']=row
        for key in ['phase','next']:
            if key in details: state[key]=details[key]
        (D/'STATE.json').write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
        text='# Wuji 承托与持续按压当前轮\n\n实际副本 `'+str(R)+'`。先读 research/support-pressure-20261003/GOAL.md 和 STATE.json。禁止子代理、自动真机动作；本轮无GPU小时上限或利用率指标。旧冻结结果不改。\n\n```json\n'+json.dumps(state,ensure_ascii=False,indent=2)+'\n```\n'
        for p in [D/'HANDOFF.md',R/'WUJI_GOAL_HANDOFF.md']:p.write_text(text)
        marker='<!-- WUJI_SUPPORT_PRESSURE_HISTORY -->'
        for p in [R.parent/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
            old=p.read_text() if p.exists() else ''; old=old.split(marker,1)[-1].lstrip('\n') if marker in old else old
            p.write_text(text+'\n'+marker+'\n'+old)
        return row
