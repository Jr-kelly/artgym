"""Import immutable remote receipts and evaluate every completed new rollout."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_highload_goal import record
from scripts.evaluate_wuji_antirotation import evaluate
from scripts.analyze_wuji_highload_cycles import analyze
R=Path(__file__).resolve().parents[1];B=R/'runs/highload-20261005';D=R/'research/highload-20261005'
def main():
 rows=[]
 for receipt in (B/'jobs').glob('*/result.json'):
  result=json.loads(receipt.read_text());marker=receipt.parent/'journal-imported.json'
  if result.get('machine','').startswith('authorized-development') and not marker.exists():
   record('remote_job_receipt_imported',evidence=str(receipt.relative_to(R)),config={k:result.get(k) for k in ['command','gpu','start_utc','end_utc','exit_code','source_archive_sha256']},next='Use actual rollout or explicit preprocessing failure; no success inferred from exit alone')
   marker.write_text(json.dumps({'imported':True}))
 for p in sorted(B.glob('**/trace.npz')):
  if 'first-two-cycles' in p.parts:continue
  if not (p.parent/'report.json').exists():continue
  trial=p.parent;r=evaluate(trial);(trial/'functional-evaluation.json').write_text(json.dumps(r,indent=2))
  cycles=analyze(trial);(trial/'cycle-diagnostics.json').write_text(json.dumps(cycles,indent=2))
  rows.append(dict(trial=str(trial.relative_to(R)),evaluation=r,diagnostics=cycles))
 (D/'DELIVERY-RESULTS.json').write_text(json.dumps(dict(scope='New development simulations, not physical robot or independent success-rate estimate. Original criterion unmodified.',trials=rows),indent=2))
 print(json.dumps([dict(trial=r['trial'],endpoints_mm={k:round(v*1000,2) for k,v in r['evaluation']['slider_endpoints_m'].items()},checks=r['evaluation']['checks']) for r in rows],indent=2))
if __name__=='__main__':main()
