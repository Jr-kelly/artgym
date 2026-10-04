"""Recoverable 24-template/12-morphology once-estimated curriculum preparation.

No rollout or training is performed. All eight height observations retain their
original gates and source failures; no behavioral outcome selects a template.
"""
import copy,hashlib,json
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');O=B/'complete-necessary-geometry24-v1';O.mkdir(exist_ok=False)
scene=json.loads((B/'strict-geometry-table-prior-prefix-v2/scene16.json').read_text());base=copy.deepcopy(scene['initial_estimated_plans']);height=[];ids=json.loads((B/'strict-geometry-learned-prefix-v1/schedule16.json').read_text())['instances'];rows=json.loads((B/'common-joint-reserve-repair-v2/height-corrected-outcomes.json').read_text())
assert len(base)==16 and len(rows)==8 and all(row['passed'] for row in rows)
for row in rows:
    folder=Path(row['output']);motor=json.loads((folder/'motor-plan.json').read_text());estimate=json.loads((folder/'estimate.json').read_text());reference=json.loads((folder/'reference.json').read_text());height.append(dict(estimate=estimate,motor_plan=motor,support_target_q=motor['post_lift_close_q'],thumb_reference=reference));ids.append(row['instance_physics_only'])
scene.update(initial_estimated_plans=base+height,repeat_initial_estimate_templates=True,resample_initial_estimates=True,table_initial_prior_from_measured_arm=True)
assert len(ids)==24 and len(set(ids))==12 and all(ids.count(sid)==2 for sid in set(ids))
(O/'scene24.json').write_text(json.dumps(scene,indent=2));heightscene=copy.deepcopy(scene);heightscene['initial_estimated_plans']=height;(O/'height-scene8.json').write_text(json.dumps(heightscene,indent=2))
registry=json.loads((B/'strict-geometry-learned-prefix-v1/registry.json').read_text());registry['entries']+=json.loads((B/'height-geometry-bank8-v1/registry.json').read_text())['entries'];(O/'registry.json').write_text(json.dumps(registry,indent=2))
for n in [24,1536]:
    (O/('schedule%d.json'%n)).write_text(json.dumps({'instances':ids*(n//24),'scope':'Physical12geometrytrainloading only, exactly2noisyinitialtemplates each, actorneverreceivesID'},indent=2))
(O/'height-schedule8.json').write_text(json.dumps({'instances':ids[16:],'scope':'Necessaryheight physicalqualification, not independentvalidation'},indent=2))
receipt={'templates':24,'physical_morphologies':12,'once_estimates_each':2,'new_height_templates':8,'source_assets':[{'instance_physics_only':entry['instance'],'path':entry['directory'],'urdf_sha256':hashlib.sha256((Path(entry['directory'])/'mobility.urdf').read_bytes()).hexdigest()} for entry in registry['entries']],'scope':'Ready-to-qualify/train configuration only; no heighttraining/residualweight/generalization success claimed. Alloriginalgeometry gates alreadycompleted, rejectedpre-repair targets retained, nobehavior filtering. Actor154/frozenR8002076 unchanged; noisy initialgeometry features6 includeheight.'}
(O/'preparation-receipt.json').write_text(json.dumps(receipt,indent=2));record('complete_necessary_geometry24_scene_prepared',config=receipt,evidence=str(O),next='Useheight-only8 qualification toverifyactualnew5s interface; heighttraining onlyifactualdevelopment supports usefulnewmethod, notblindfailedextension')
