"""Record this hold experiment in durable task and shared handoffs."""
import argparse
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def record(event, summary, evidence, next_step):
    for path in evidence:
        assert (ROOT / path).exists(), path
    item = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                event=event, summary=summary, evidence=evidence, next=next_step)
    for path in [ROOT/'runs/hold-20260929/events.jsonl', ROOT.parent/'runs/wuji-goal/journal/events.jsonl']:
        with path.open('a') as stream:
            stream.write(json.dumps(item, ensure_ascii=False)+'\n')
    entry = '\n## '+item['time']+' '+event+'\n\n'+summary+'\n证据：'+', '.join(evidence)+'。下一步：'+next_step+'。\n'
    for path in [ROOT/'WUJI_HOLD_HANDOFF.md', ROOT.parent/'WUJI_GOAL_HANDOFF.md', Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
        with path.open('a') as stream:
            stream.write(entry)
    print(json.dumps(item, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--evidence', nargs='+', required=True)
    parser.add_argument('--next', required=True)
    args = parser.parse_args()
    record(args.event, args.summary, args.evidence, args.next)
