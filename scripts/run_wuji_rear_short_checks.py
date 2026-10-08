"""Bounded decision-oriented short checks; never training or full pickup repetition."""
import json,subprocess,sys
from pathlib import Path
from scripts.record_wuji_rear_event import record
s=json.loads(Path('research/rear-sim2real-20261009/SHORT-CHECKS.json').read_text())
for name,args in s['cases']:
    out=Path('runs/rear-sim2real-20261009/short-checks')/name
    log=out.parent/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as f:r=subprocess.run([sys.executable,'-m','scripts.run_wuji_rear','sim','--bundle','research/rear-sim2real-20261009/bundle.json','--output',str(out)]+args,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:
        record('short_check_process_failure',[log],dict(case=name,returncode=r.returncode));raise SystemExit(r.returncode)
    result=json.loads((out/'result.json').read_text());print(json.dumps(dict(case=name,passed=result['passed'],advance_mm=result['active_displacement_mm'],rotation=result['body_max_rotation_rad'])),flush=True)
