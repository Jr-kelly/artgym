"""Keep per-source frozen-history fitting distinct from changing-policy rollouts."""
import csv,json,re
from pathlib import Path

def main():
 root=Path('runs/unified-student-20261001');out=Path('research/unified-student-20261001');rows=[]
 for path in sorted(root.glob('*-development/*-S2/holdout-errors.json')):
  name=path.parent.name[:-3];match=re.search(r'-(\d+)$',name)
  if not match:continue
  step=int(match.group(1));method=name[:match.start()]
  folders={'S0':['S0-3200'],'C1':['C1-3200'],'SC-real':['SC-real-6400','SC-real-12800'],'SC-masked':['SC-masked-6400-r1','SC-masked-12800'],'SA-real':['SA-real-12800']}
  training=[]
  for folder in folders.get(method,[]):
   p=root/folder/'learning.jsonl'
   if p.exists():training += [json.loads(line) for line in p.read_text().splitlines()]
  tail=[r for r in training if step-100<r['update']<=step]
  for r in json.loads(path.read_text()):
   source=r['source'];row=dict(model=name,optimizer_step=step,source=source,teacher_history_protocol=Path(r['probes']).parent.name.split('-')[-1],holdout_latent_mse=r['latent_mse'],holdout_raw_mean_mse=r['raw_mean_mse'],holdout_clipped_action_mse=r['clipped_action_mse'],holdout_target_mse_rad2=r['target_mse_rad2'],teacher_history_episodes=r['independent_initial_states'],sampled_times_per_episode=r['sampled_times'],own_rollout_latent_mse_tail100=sum(x['source_mse'][source] for x in tail)/len(tail) if tail else None,training_rows_available=len(tail))
   analysis=out/(name+'-development-analysis')/'report.json'
   if analysis.exists():
    a=json.loads(analysis.read_text());cell=next((c for c in a['rows'] if c['model']==name and c['source']==source and c['protocol']==row['teacher_history_protocol']),None)
    if cell:row.update(strict_success=cell['success'],n=cell['n'],body_stable=cell['body_stable'],phase_hold=cell['phase_hold'],worst_stage_hold=cell['worst_stage_hold'])
   rows.append(row)
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (out/'fit-versus-closedloop.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 (out/'fit-versus-closedloop.json').write_text(json.dumps(dict(scope='Development only. Frozen teacher-history probes are never optimized; sampled times are correlated. Own-rollout loss is on changing distributions and not directly comparable across policies.',rows=rows),indent=2))
 print('Rows',len(rows))
if __name__=='__main__':main()
