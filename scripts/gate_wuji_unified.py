"""Apply frozen per-source strict/body promotion rules, no checkpoint retuning."""
import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--references',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=json.loads(a.candidate.read_text())['rows'];refs=json.loads(a.references.read_text())['rows'];results=[]
 for model in sorted(set(r['model'] for r in rows)):
  cells=[]
  for x in [r for r in rows if r['model']==model]:
   r=next(r for r in refs if r['model']==('source3' if x['source']==3 else 'historical') and r['source']==x['source'] and r['seconds']==x['seconds']);assert r['n']==x['n']
   checks=dict(strict_absolute=x['rate']>=.8,strict_reference=x['rate']>=r['rate']-.1-1e-9,body_absolute=x['body_rate']>=.95,body_reference=x['body_rate']>=r['body_rate']-.03-1e-9)
   cells.append(dict(**x,expert_rate=r['rate'],expert_body_rate=r['body_rate'],checks=checks,passed=all(checks.values())))
  assert len(cells)==8
  results.append(dict(model=model,passed=all(c['passed'] for c in cells),worst_strict=min(c['rate'] for c in cells),worst_body=min(c['body_rate'] for c in cells),macro_strict=sum(c['rate'] for c in cells)/8,cells=cells))
 ranked=sorted(results,key=lambda r:(-r['worst_strict'],-r['worst_body'],-r['macro_strict'],int(''.join(c for c in r['model'] if c.isdigit()) or 0)))
 out=dict(results=results,selected_model=ranked[0]['model'],selection='max worststrict,thenworstbody,thenmacro,thenearlier checkpoint epoch',scope='Development checkpoint choice only; final results cannot change selection')
 assert not a.output.exists();a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(selected_model=out['selected_model'],results=[{k:v for k,v in r.items() if k!='cells'} for r in results])))
if __name__=='__main__':main()
