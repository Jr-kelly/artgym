"""One paired causal check: matching initial scene with/without exploration.
Not a success-rate sweep; actor/geometry/load/randomization identical.
"""
import subprocess,json
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';results=[]
for stochastic in [False,True]:
 name='three-geometry-randomized-'+('stochastic' if stochastic else 'deterministic')+'-causal-v6';out=C/name;args=['-m','scripts.probe_wuji_antirotation_module','--scene',str(C/'scene4.json'),'--reference',str(B/'initial-geometry-v2/projected-00/reference-v1.json'),'--asset-registry',str(C/'registry.json'),'--geometry-schedule',str(C/'schedule8.json'),'--checkpoint','runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth','--randomization-scale','.5','--output',str(out)]
 if stochastic:args+=['--stochastic-residual']
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True);j=json.loads((out/'report.json').read_text());results.append(dict(stochastic=stochastic,episodes=j['episodes']));record('three_geometry_fitting_failure_causal_probe_closed',config={'stochastic':stochastic,'scope':'Eight same-start actual train-geometry episodes; informative mechanism check, not independent statistics'},evidence=str(out),next='Distinguish placement/material/estimate fragility from exploratory command jitter; no parameter sweep')
(C/'causal-exploration-comparison.json').write_text(json.dumps(results,indent=2))
