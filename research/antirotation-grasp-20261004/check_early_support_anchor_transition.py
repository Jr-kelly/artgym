"""Actual earlylift correction around reachable known supportreference, no actor truth."""
import subprocess,json
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';O=B/'early-support-anchor-v1';O.mkdir(exist_ok=False);PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
for enabled in [False,True]:
 scene=json.loads((C/'scene4.json').read_text());scene['scheduled_support_anchor']=enabled;sp=O/('scene-'+str(enabled)+'.json');sp.write_text(json.dumps(scene,indent=2));name='earlylift-known-support-anchor-'+str(enabled)+'-v15';out=O/name
 args=['-m','scripts.probe_wuji_antirotation_module','--scene',str(sp),'--reference',str(B/'initial-geometry-v2/projected-00/reference-v1.json'),'--asset-registry',str(C/'registry.json'),'--geometry-schedule',str(C/'schedule8.json'),'--envs','8','--takeover-seconds','8','--output',str(out)]
 record('earlylift_support_anchor_pair_started',config={'scheduled_support_anchor':enabled,'actor':'zero residual around knowngeometryreference','takeover_s':8,'resistance_N':[.2,.2],'scope':'Actualpickup/twocycles, nominal/thin/thick compatibility; no currenttruthactorinput/constantforce. Oldfixedanchor clips planned supporttransition, newknownreference keeps boundedresidual relativeto plan'},evidence=str(out),next='Judge actual fullflow support and preserve originaldefault; newtraining only after mechanistic compatibility')
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
 e=json.loads((out/'report.json').read_text())['episodes'];summary={'n':len(e),'pickup':sum(r['pickup_valid'] for r in e),'fall':sum(r['fall'] for r in e)};(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');record('earlylift_support_anchor_pair_closed',config=summary,evidence=str(out),next='Compare reachablepreload actual support/returns, not smallsuccessrate decimals')
