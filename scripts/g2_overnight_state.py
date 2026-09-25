"""Durable overnight state/journal. Does not launch or stop external tasks."""
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/g2-overnight-20260926'

def main():
    p=argparse.ArgumentParser();p.add_argument('--message',required=True)
    p.add_argument('--next-action');p.add_argument('--hypothesis');p.add_argument('--furthest')
    p.add_argument('--round',type=int);p.add_argument('--direction-review',action='store_true');a=p.parse_args()
    state=json.loads((RUN/'task-state.json').read_text());now=datetime.now(timezone.utc)
    records=[]
    for f in sorted(RUN.glob('*-process.json')):
        r=json.loads(f.read_text());pid=r.get('pid');proc=Path('/proc')/str(pid)/'stat'
        alive=False
        if proc.exists():
            fields=proc.read_text().split(') ')[1].split()
            alive=fields[0]!='Z' and (r.get('process_start_ticks') is None or fields[19]==str(r['process_start_ticks']))
        records.append(dict(name=f.name[:-len('-process.json')],pid=pid,alive=alive,exit_code=r.get('exit_code'),round=r.get('round',1),kind=r.get('kind','control')))
    state['processes']=records
    state['used']['control_launches']=sum(r['kind']=='control' for r in records)
    state['used']['validation_launches']=sum(r['kind']=='validation' for r in records)
    for attr in ['next_action','hypothesis','furthest','round']:
        value=getattr(a,attr)
        if value is not None:state[attr]=value
    state['updated_utc']=now.isoformat();state['latest_message']=a.message
    if a.direction_review:state['direction_review_due_utc']=(now+timedelta(minutes=90)).isoformat()
    (RUN/'task-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    event=dict(time_utc=now.isoformat(),message=a.message,used=state['used'],next_action=state['next_action'],round=state['round'])
    for f in [RUN/'journal.jsonl',ROOT/'runs/wuji-goal/journal/events.jsonl']:
        with f.open('a') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
    marker='\n## Overnight G2 20260926 '+now.isoformat()+'\n\n'+a.message+'\n\n续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。\n'
    for f in [ROOT/'G2_TABLETOP_HANDOFF.md',ROOT/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:f.write_text(marker+f.read_text())
    print(json.dumps(event,ensure_ascii=False))

if __name__=='__main__':main()
