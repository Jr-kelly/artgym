"""Append-only continuation for the isolated fixed-grasp deployment work."""
import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CENTRAL=Path('/data/research/artgym-experiments-20260921')
ACTOR='runs/newknife-20261005/train/center-tail-constant-motor-v1/update_000100.pth'
def record(event,evidence=(),config=None,next_step='Continue fixed-grasp deployment; preserve pickup/regrasp evidence'):
    row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,root=str(ROOT),evidence=list(map(str,evidence)),config=config or {},actor_sha256=hashlib.sha256((ROOT/ACTOR).read_bytes()).hexdigest(),next=next_step,real_robot_ran=False)
    for p in [CENTRAL/'runs/wuji-goal/journal/events.jsonl',ROOT/'research/rear-sim2real-20261009/events.jsonl']:
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False,default=str)+'\n')
    section='# 固定握姿后段部署当前轮 2026-10-09\n\n实际独立副本：`'+str(ROOT)+'`。先读本副本 `research/rear-sim2real-20261009/CONTINUATION.md`（生成后）。保留下面取物／换握成果；当前优先级由用户附件改为固定腕姿、人工摆刀后的后段部署，不自动长训。\n\n```json\n'+json.dumps(row,ensure_ascii=False,indent=2,default=str)+'\n```\n\n<!-- WUJI_REAR_HISTORY -->\n'
    for p in [Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),CENTRAL/'WUJI_GOAL_HANDOFF.md',ROOT/'WUJI_GOAL_HANDOFF.md']:
        old=p.read_text(encoding="utf-8"); marker='<!-- WUJI_REAR_HISTORY -->\n'
        if marker in old:old=old.split(marker,1)[1]
        p.write_text(section+old,encoding="utf-8")
    return row
if __name__=='__main__':
    import sys
    print(json.dumps(record(sys.argv[1]),ensure_ascii=False))
