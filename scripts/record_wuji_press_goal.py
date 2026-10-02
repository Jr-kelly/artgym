"""Durable ledger for this round only; never modifies a closed round."""
import datetime
import fcntl
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / 'research/real-knife-press-resistance-20261002'


def record(event, **details):
    D.mkdir(parents=True, exist_ok=True)
    with (D / '.event.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = datetime.datetime.now(datetime.timezone.utc)
        row = dict(utc=now.isoformat(), event=event, **details)
        for p in [D / 'DECISIONS.jsonl', R.parent / 'runs/wuji-goal/journal/events.jsonl']:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        state = json.loads((D / 'STATE.json').read_text())
        state.update(details.get('state_updates', {}))
        state['last_event'] = row
        for key in ['phase', 'next']:
            if key in details:
                state[key] = details[key]
        jobs = R / 'runs/real-knife-press-resistance-20261002/jobs'
        state['active_jobs'] = [json.loads(p.read_text()) for p in jobs.glob('*/identity.json')
                                if not (p.parent / 'result.json').exists()]
        state['new_gpu_hours'] = sum(json.loads(p.read_text())['gpu_hours']
                                     for p in jobs.glob('*/result.json'))
        state['cumulative_gpu_hours'] = state['historical_gpu_hours'] + state['new_gpu_hours']
        state['remaining_gpu_hours'] = state['max_gpu_hours'] - state['cumulative_gpu_hours']
        state['active_gpu_elapsed_hours'] = sum(
            max(0, (now - datetime.datetime.fromisoformat(j['start_utc'])).total_seconds())
            * j.get('gpu_count', 1) / 3600 for j in state['active_jobs'])
        state['remaining_including_active'] = state['remaining_gpu_hours'] - state['active_gpu_elapsed_hours']
        encoded = json.dumps(state, ensure_ascii=False, indent=2) + '\n'
        tmp = D / 'STATE.tmp'
        tmp.write_text(encoded)
        tmp.replace(D / 'STATE.json')
        message = ('# 当前 Wuji 实物刀持续按压与阻力 Goal\n\n工作区 `' + str(R) +
                   '`。先读 research/real-knife-press-resistance-20261002/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。'
                   '禁止子代理；旧最终集关闭。PID/利用率均须重新核实。\n\n```json\n' + encoded + '```\n')
        for p in [D / 'HANDOFF.md', R / 'WUJI_GOAL_HANDOFF.md']:
            p.write_text(message)
        marker = '<!-- REAL_KNIFE_PRESS_HISTORY -->'
        for p in [R.parent / 'WUJI_GOAL_HANDOFF.md', Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
            old = p.read_text() if p.exists() else ''
            if marker in old:
                old = old.split(marker, 1)[1].lstrip('\n')
            p.write_text(message + '\n' + marker + '\n' + old)
        return row
