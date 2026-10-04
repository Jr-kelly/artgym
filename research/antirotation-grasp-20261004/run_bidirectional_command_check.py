import json,subprocess,time
from pathlib import Path
B=Path('runs/antirotation-grasp-20261004');p=B/'jobs/bidirectional-tangential-preload-original-motor-audit-v1/result.json'
while not p.exists():time.sleep(5)
assert json.loads(p.read_text())['exit_code']==0,'Rejected direction geometry, no execution'
py='/home/agiuser/miniconda3/envs/artgym/bin/python';subprocess.run([py,'-m','scripts.run_wuji_antirotation_job','--name','bidirectional-known-schedule-command-check-v1','--',py,'-m','research.antirotation-grasp-20261004.verify_bidirectional_reference'],check=True)
