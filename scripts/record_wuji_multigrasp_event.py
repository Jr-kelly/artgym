"""Append a bounded task event to all required local handoff and journal locations."""
import argparse,datetime,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--event',required=True);p.add_argument('--summary',required=True);p.add_argument('--evidence',nargs='+',required=True);p.add_argument('--next',required=True);a=p.parse_args()
 for evidence in a.evidence:
  path=Path(evidence);path=path if path.is_absolute() else R/path
  if not path.exists():raise FileNotFoundError('Evidence path does not exist: '+str(path))
 row=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=a.event,summary=a.summary,evidence=a.evidence,next=a.next,reference_weight_sha256='4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac')
 for file in [R/'runs/multigrasp-20260928/events.jsonl',R.parent/'runs/wuji-goal/journal/events.jsonl']:
  with file.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 for file in [R/'WUJI_MULTIGRASP_HANDOFF.md',R.parent/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
  with file.open('a') as f:f.write('\n## 多抓姿 '+row['time']+' '+a.event+'\n\n'+a.summary+' 证据：'+', '.join(a.evidence)+'。下一步：'+a.next+'。\n')
 print(json.dumps(row,ensure_ascii=False))
if __name__=='__main__':main()
