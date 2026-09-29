"""Index actual saved checkpoint hashes, optimizer state and training provenance."""
import datetime,hashlib,json
from pathlib import Path
import torch
R=Path(__file__).resolve().parents[1];B=R/'runs/unified-policy-20260930';Q=R/'research/unified-policy-20260930'
def main():
 selected=json.loads((Q/'final-freeze.json').read_text())['candidate']['sha256'];rows=[]
 for p in sorted(B.glob('*/*.pth')):
  h=hashlib.sha256(p.read_bytes()).hexdigest();c=torch.load(p,map_location='cpu');c=c[0] if 0 in c else c;s=c['model'];assert all(torch.isfinite(v).all() for v in s.values())
  rows.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=h,selected_unified=h==selected,kind=c.get('training_kind','historical expert or normalization-compensated expert'),epoch=c.get('bc_epoch',c.get('epoch')),bc_updates=c.get('bc_updates'),optimizer='bc_optimizer' if 'bc_optimizer' in c else 'optimizer' if 'optimizer' in c else None,bc_rng_preserved=all(k in c for k in ['bc_torch_rng','bc_cuda_rng','bc_numpy_rng']),init_sha256=c.get('bc_manifest',{}).get('init_sha256'),normalization_rebase=c.get('normalization_rebase'),model_tensors=len(s),all_model_tensors_finite=True))
 out=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected_sha256=selected,rows=rows,scope='Saved files including untouched parent experts, perturbed initializations, pilots, all saved BC milestones and actual recovery audit; no checkpoint implies G2success')
 (Q/'weights-index.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(checkpoints=len(rows),selected_sha256=selected)))
if __name__=='__main__':main()
