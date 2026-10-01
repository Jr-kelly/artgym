"""Durable current-round events, state and cross-workspace handoff."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / 'research/unified-student-20261001'


def record(event, **details):
    with (D / '.event.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        row = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=event, **details)
        for path in [D / 'DECISIONS.jsonl', R.parent / 'runs/wuji-goal/journal/events.jsonl']:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        state = json.loads((D / 'STATE.json').read_text())
        state['last_event'] = row
        jobs = R / 'runs/unified-student-20261001/jobs'
        if jobs.exists():
            state['active_jobs'] = [json.loads(p.read_text()) for p in jobs.glob('*/identity.json') if not (p.parent/'result.json').exists()]
            state['gpu_hours'] = sum(json.loads(p.read_text())['gpu_hours'] for p in jobs.glob('*/result.json'))
        (D / 'STATE.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        message = ('# 当前统一 student Goal\n\n工作区 `' + str(R) + '`\n\n'
            '先读 research/unified-student-20261001/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。'
            '禁止子代理；旧teacher最终集关闭。PID/利用率须重新核验，不据旧日志重启。\n\n'
            '```json\n' + json.dumps(state, ensure_ascii=False, indent=2) + '\n```\n')
        for path in [D / 'HANDOFF.md', R / 'WUJI_GOAL_HANDOFF.md']:
            path.write_text(message)
        for path in [R.parent / 'WUJI_GOAL_HANDOFF.md', Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
            old = path.read_text() if path.exists() else ''
            marker = '<!-- STUDENT_HISTORY -->'
            if marker in old:
                old = old.split(marker, 1)[1].lstrip('\n')
            path.write_text(message + '\n' + marker + '\n' + old)
        return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('event')
    parser.add_argument('details')
    args = parser.parse_args()
    print(json.dumps(record(args.event, **json.loads(args.details)), ensure_ascii=False))
