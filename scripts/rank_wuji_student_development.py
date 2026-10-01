"""Apply the preregistered development ranking; never read final evaluations."""
import json,math,re
from pathlib import Path

def main():
 root=Path('research/unified-student-20261001');ranked=[]
 for path in root.glob('*-development-analysis/report.json'):
  report=json.loads(path.read_text())
  for name,gate in report.get('gates',{}).items():
   rows=[r for r in report['rows'] if r['model']==name]
   if len(rows)!=12 or any(r['n']!=32 for r in rows):continue
   ss=[r for r in rows if r['protocol']!='F'];deficits=[]
   for r in rows:
    teacher=next(t for t in report['rows'] if t['model']=='teacher' and t['source']==r['source'] and t['protocol']==r['protocol'])
    n=r['n'];required=math.ceil(max(.8*n,teacher['success']-.1*n if r['protocol']!='F' else 0)-1e-9)
    d=dict(protocol=r['protocol'],source=r['source'],strict_deficit=max(0,required-r['success']))
    if r['protocol']!='F':d['body_deficit']=max(0,math.ceil(max(.95*n,teacher['body_stable']-.03*n)-1e-9)-r['body_stable'])
    deficits.append(d)
   worst=max(max(d['strict_deficit'],d.get('body_deficit',0)) for d in deficits)
   step=int(re.search(r'(\d+)$',name).group(1)) if re.search(r'(\d+)$',name) else 0
   key=[int(gate['passed']),min(r['rate'] for r in ss),min(r['worst_stage_hold'] for r in ss),min(r['body_rate'] for r in ss),-step]
   ranked.append(dict(model=name,ranking_key=key,evidence=str(path),complete_gate=gate['passed'],worst_missing_episode_count=worst,confirmation_eligible=worst<=1,deficits=deficits))
 ranked.sort(key=lambda r:r['ranking_key'],reverse=True)
 out=dict(scope='Provisional development ranking only. Full or within-one-episode across all required cells is eligible for64 confirmation; no final files read.',ranking=ranked)
 (root/'development-ranking.json').write_text(json.dumps(out,indent=2));print(json.dumps(ranked[:3]))
if __name__=='__main__':main()
