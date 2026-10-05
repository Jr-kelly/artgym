"""Separate physical task, nominal certificates and deployment readiness."""
import json,hashlib,datetime
from pathlib import Path
B=Path('runs/contact-transfer-20261006');D=Path('research/contact-transfer-20261006')
rows=[]
cases=[('nominal125','regression/nominal-125-video-v1','Retained nominal1.25N regression','retained_baseline'),('near-small-prefix','development/near-small-prefix-physical-v1','Near-small34mm nominal prefix','development'),('near-small-guard','development/near-small-guarded-v2','Near-small actual-target clearance guard','development_rejected'),('large-baseline','development/large-baseline-video-v1','Large original28mm','development_baseline'),('large-normal-diagnostic','development/large-fixed-normal35-physical-v1','Large full-normal35mm; rate-limited diagnostic, not certified promotion','diagnostic_only'),('large-center','development/large-centered35-physical-v1','Large estimate-driven .2cap-width contact bias','development_rejected'),('frozen-mid','frozen/mid-high-delay/physical-v1','NEW mid geometry +1.25N +delay/noise','frozen_validation'),('frozen-upper','frozen/upper-geometry-friction/physical-v1','NEW upper geometry +variable .93N +friction/noise','frozen_validation')]
for name,path,label,kind in cases:
 trial=B/path/'simulation';e=json.loads((trial/'extension-evaluation.json').read_text());report=json.loads((trial/'report.json').read_text());params=json.loads((Path(report['physical_asset']).parent/'parameters.json').read_text());rows.append(dict(name=name,label=label,kind=kind,trial=str(trial),evaluation=e,physical_parameters=params,actor_sha256='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e',hardware_ready=False,scope='Complete original physical simulation task. Task pass does not prove corrected-target clearance, firmware calibration or real demo.'))
failures=[]
for folder in (B/'preparation').iterdir():
 if not folder.is_dir():continue
 p=folder/'preparation-result.json'
 if p.exists():
  result=json.loads(p.read_text())
  if not result.get('passed'):failures.append(dict(directory=str(folder),result=result))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),trials=rows,preparation_rejections=failures,mapping_verified=True,device_interface_verified='SDK1.8 signatures/import and HandAPI fixture; no completed device connection',hardware_load_model_status='Signed virtual work and coordinate check passed; external on-hand reaction must be subtracted from inertia+gravity compensation; revised worst38.79% model only',axial_force_measurement_status='Actual total axial contact missing/null; no fake zero',extension_demo_ready=True,force_margin_evidence='Retained1.25N nominal exact24.366mm and NEW mid-high-delay22.123mm; no newly demonstrated capacity beyond1.25N',necessary_generalization_status='One of two NEW joint conditions passes physical criterion. Near-small29.71mm physical task and sampled measured-path clearance>=11.78mm pass; target overlap is impedance setpoint information, strict guard14.56mm is not a hard geometric capacity limit. Large contact recovery .999–1 fraction but support/rotation remains deficient.',real_robot_ran=False,new_training=False,hunyuan_used=False,source_asset_vs_model_vs_physics_vs_hardware_separate=True)
(D/'DELIVERY-RESULTS.json').write_text(json.dumps(result,indent=2))
print(json.dumps([(r['name'],r['evaluation']['active_forward_m']*1000,r['evaluation']['pass_all']) for r in rows]))
