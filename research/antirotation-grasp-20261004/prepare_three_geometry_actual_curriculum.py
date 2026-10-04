"""Actual-developed nominal/thin/thick shared-policy curriculum configuration."""
import json,hashlib
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=Path('research/antirotation-grasp-20261004');O=B/'three-geometry-curriculum-v1';O.mkdir(parents=True,exist_ok=False)
scene=json.loads((D/'projected-real-nominal-training-scene-v3.json').read_text());records=[]
for root,ref in [('initial-geometry-v2/projected-00','reference-v1.json'),('initial-geometry-v5/thin-projected04-allcontacts','reference.json'),('initial-geometry-v2/projected-08','reference-v1.json'),('initial-geometry-v2/projected-00','reference-v1.json')]:
 p=B/root;motor=json.loads((p/'motor-plan.json').read_text());records.append(dict(estimate=motor['initial_geometry_estimate'],motor_plan=motor,support_target_q=motor['post_lift_close_q'],thumb_reference=json.loads((p/ref).read_text())))
scene.update(initial_estimated_plans=records,repeat_initial_estimate_templates=True,resample_initial_estimates=False)
(O/'scene4.json').write_text(json.dumps(scene,indent=2));ids=['real-nominal','t0001','t0002','real-nominal'];entries=[dict(instance=sid,directory='assets/objects/knife_wuji_real_size_20261002/000/' if sid=='real-nominal' else 'assets/objects/knife_wuji_dense_under_20261003/'+sid+'/',split='train') for sid in ['real-nominal','t0001','t0002']];(O/'registry.json').write_text(json.dumps({'entries':entries},indent=2))
for n in [8,4096]:(O/('schedule%d.json'%n)).write_text(json.dumps({'instances':ids*(n//4),'scope':'Physical train loading only, excluded from actor/common geometry mechanism'},indent=2))
record('three_actual_developed_geometry_curriculum_prepared',evidence=str(O),config={'templates':4,'physical_train_geometries':3,'controller':'Same frozen750 legal154 inputs, original .04 supportspan/.025support/.12thumb','planned_load_band_N':[.1,.35],'planned_start_band_N':[.1,.35],'scope':'Actual developed noisy nominal/thin/thick paths. Nominal/thick retain their measured positive clearances and failed300um reserve where recorded; no physics relaxation or independentgen claim. New strict common sixteen-estimate bank continues separately.'},next='Eight actual physical compatibility trajectories with matched loading/initial estimates before useful common geometry pilot')
