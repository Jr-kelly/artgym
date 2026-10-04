"""One fixed-policy batch physics resource diagnosis, no learning or score tuning."""
import subprocess,json
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
for label,rand,capacity in [('zero-noise-original',0,None),('mixed-noise-larger-buffer',.5,8388608)]:
 name='batch-physics-'+label+'-v8';args=['-m','scripts.probe_wuji_antirotation_module','--scene',str(C/'scene4.json'),'--reference',str(B/'initial-geometry-v2/projected-00/reference-v1.json'),'--asset-registry',str(C/'registry.json'),'--geometry-schedule',str(C/'schedule4096.json'),'--checkpoint','runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth','--envs','4096','--trace-envs','8','--randomization-scale',str(rand),'--output',str(C/name)]
 if capacity:args+=['--physx-contact-pairs',str(capacity)]
 record('batch_physics_capacity_diagnostic_started',config={'envs':4096,'randomization':rand,'capacity':capacity,'scope':'Fixed actor numerical validity diagnosis; no PPO or independent generalization claim'},evidence=str(C/name),next='Compare population pathology with all perturbations zero and explicit contact capacity')
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
 report=json.loads((C/name/'report.json').read_text());e=report['episodes'];summary={'n':len(e),'pickup':sum(x['pickup_valid'] for x in e),'fall':sum(x['fall'] for x in e),'randomization':rand,'capacity':capacity};(C/name/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');record('batch_physics_capacity_diagnostic_closed',config=summary,evidence=str(C/name),next='Repair proven cause only; do not extend negative fits')
