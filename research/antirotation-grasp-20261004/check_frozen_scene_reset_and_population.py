"""Causal physical validity check after small probes did not explain fit failures.
Unchanged frozen actor, no optimization or success-rate tuning. Trace stores
predeclared representative indices only; all episode results are retained.
"""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
for n,episodes,label in [(8,2,'reset'),(4096,1,'population')]:
 name='three-geometry-frozen750-'+label+'-causal-v7';args=['-m','scripts.probe_wuji_antirotation_module','--scene',str(C/'scene4.json'),'--reference',str(B/'initial-geometry-v2/projected-00/reference-v1.json'),'--asset-registry',str(C/'registry.json'),'--geometry-schedule',str(C/('schedule%d.json'%n)),'--checkpoint','runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth','--envs',str(n),'--episodes',str(episodes),'--trace-envs','8','--randomization-scale','.5','--output',str(C/name)]
 record('frozen_physical_reset_population_causal_check_started',config={'envs':n,'episodes':episodes,'scope':'One reset/policy-population validity question, no training/independent success-rate claim'},evidence=str(C/name),next='Compare unchanged actor actual pickup/fall before blaming learning; no unchanged failed training extension')
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True);record('frozen_physical_reset_population_causal_check_closed',evidence=str(C/name),next='Read reset/population physical outcome and choose a substantive repair only if demonstrated')
