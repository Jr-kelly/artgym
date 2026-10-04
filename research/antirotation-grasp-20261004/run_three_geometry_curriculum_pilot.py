"""New shared actual-grasp curriculum after matched physical compatibility.
Capped100; freeze50 physical thin check stops unchanged failures early.
"""
import json,time,subprocess,os,signal,hashlib
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');C=B/'three-geometry-curriculum-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';gate=B/'jobs/three-geometry-frozen750-physical-compatibility-v5/result.json'
while not gate.exists():time.sleep(5)
assert json.loads(gate.read_text())['exit_code']==0
compat=json.loads((C/'frozen750-compatibility/report.json').read_text());assert len(compat['episodes'])==8 and all(row['pickup_valid'] and not row['fall'] for row in compat['episodes']),'Reject unqualified physical scene; do not train failures'
name='actual-three-geometry-retain750-curriculum-v5';a=json.loads((B/'jobs/actual-projected-realnominal-retain750-v4/identity.json').read_text())['command'];values={'--output':str(B/'train'/name),'--updates':'100','--initial-estimate-scene':str(C/'scene4.json'),'--training-geometry-schedule':str(C/'schedule4096.json'),'--training-asset-registry':str(C/'registry.json'),'--load-min':'.1','--load-max':'.35','--detent-min':'.1','--detent-max':'.35','--seed':'2026100453'}
for k,v in values.items():a[a.index(k)+1]=v
record('qualified_three_geometry_actual_curriculum_started',evidence=str(C),config={'max_updates':100,'frozen_behavior_check_update':50,'change':'Same retained750 outputs, three actually developed onceestimated contact topologies/sizeextremes, progressive.1--.35 nonzero mixed resistance, original .04 support/.025scale/.12thumb. Prior negative nominal.2--.6 not extended.'},next='Frozen50 actual thin geometry full-flow check; stop if no functional behavior improvement, broaden only with evidence')
train=subprocess.Popen([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--']+a)
weight=B/'train'/name/'update_000050.pth'
while not weight.exists():
 assert train.poll() is None,'Training ended before frozen50';time.sleep(5)
time.sleep(2)
a=json.loads((B/'jobs/actual-table-thin-allcontact-frozen750-load2-v24/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-thin-threegeo-frozen50-load2-v25';a[a.index('--output')+1]=str(trial);a[a.index('--residual-checkpoint')+1]=str(weight)
for job,args in [(trial.name,a),(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])]:subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',job,'--',PY]+args,check=True)
result=json.loads((trial/'functional-evaluation.json').read_text())
if not result['continuous_pickup_demo_pass']:
 identity=json.loads((B/'jobs'/name/'identity.json').read_text());os.kill(identity['pid'],signal.SIGTERM);record('three_geometry_curriculum_frozen50_negative_graceful_stop',config={'pid':identity['pid'],'signal':'SIGTERM handled at update boundary to save model/Adam/RNG','scope':'No unchanged extension after actual functional check'},evidence=str(trial),next='Inspect changed geometry/control mechanics; keep frozen750 best baseline')
else:record('three_geometry_curriculum_frozen50_actual_functional_improvement',config={'weight_sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'scope':'Thin traingeometry developmentcase; no independentgen'},evidence=str(trial),next='Complete initiallycapped100; check actual dimensions/load support before further curriculum')
code=train.wait();assert code==0
record('three_geometry_actual_curriculum_closed',evidence=str(B/'train'/name),next='Read frozen behavior and necessary common-bank geometry evidence; no success inferred from fitting statistics')
