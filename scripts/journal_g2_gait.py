"""Append concise durable state and synchronize the user's continuation entry."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--message',required=True);a=p.parse_args()
    run=ROOT/'runs/g2-finger-gait-20260926';run.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).isoformat();launched=sorted(p.name for p in run.glob('*-process.json'))
    event=dict(time=stamp,message=a.message,development_launches=len(launched),budget=18,process_records=launched)
    for file in [run/'journal.jsonl',ROOT/'runs/wuji-goal/journal/events.jsonl']:
        file.parent.mkdir(parents=True,exist_ok=True)
        with file.open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    note='\n## G2 分指换握 '+stamp+'\n\n'+a.message+'\n\n本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动'+str(len(launched))+'/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。\n'
    for file in [ROOT/'G2_TABLETOP_HANDOFF.md',ROOT/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
        file.write_text(note+file.read_text())
    print(json.dumps(event,ensure_ascii=False))


if __name__=='__main__':main()
