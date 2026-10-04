"""Numerical-origin causal intervention. Inter-environment collision groups unchanged."""
import subprocess,json
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
for n in [8,4096]:
 name='compact-isolated-batch%d-zero-noise-v9'%n
 args=['-m','scripts.probe_wuji_antirotation_module','--scene',str(C/'scene4.json'),'--reference',str(B/'initial-geometry-v2/projected-00/reference-v1.json'),'--asset-registry',str(C/'registry.json'),'--geometry-schedule',str(C/('schedule%d.json'%n)),'--checkpoint','runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth','--envs',str(n),'--trace-envs','8','--compact-isolated-layout','--output',str(C/name)]
 record('compact_physics_origin_causal_probe_started',config={'n':n,'randomization':0,'origin':'coincident, distinct original collisiongroups','scope':'Originalcontacts/geometry/gravity/torque unchanged; purely world-coordinate numerical hypothesis, no training'},evidence=str(C/name),next='Check isolated8 and4096 against spaced origins; no functional/gen claim')
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
 e=json.loads((C/name/'report.json').read_text())['episodes'];summary={'n':len(e),'pickup':sum(x['pickup_valid'] for x in e),'fall':sum(x['fall'] for x in e)};(C/name/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');record('compact_physics_origin_causal_probe_closed',config=summary,evidence=str(C/name),next='Only adopt batch layout if numerical pathology substantively repaired, no criterion changes')
