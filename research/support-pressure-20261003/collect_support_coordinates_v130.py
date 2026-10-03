import datetime,hashlib,json,pathlib
from scripts.record_wuji_support_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/support-pressure-20261003';B=R/'runs/support-pressure-20261003'
entries=[]
for v in ['joint','jointfrozen','normal','normalfrozen']:
 for label in ['nominal','raised1']:
  name=label+'-'+v+'-support-coordinates-v130';folder=B/'demo'/name;job=B/'jobs'/name
  result=json.loads((job/'result.json').read_text());assert result['exit_code']==0
  r=json.loads((folder/'report.json').read_text());entries.append(dict(name=name,report=str((folder/'report.json').relative_to(R)),weight_sha256=result['weight_sha256'],full_success=r['full_success'],body_rotation_rad=r['operation_body_max_rotation_rad'],endpoints_m=r['endpoints_mean_last03s_m'],pair_pressure=r['pair_pressure']))
receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),entries=entries,scope='8 matched development continuous episodes; not independent or hardware validation',conclusion='No substantial nominal repair. Retain inherited750/stagedsupport; stop coordinate and quietpreparation extension, no threshold optimization.')
(D/'support-coordinate-native-v130-results.json').write_text(json.dumps(receipt,indent=2))
weights=[]
for v in ['joint','jointfrozen','normal','normalfrozen']:
 p=B/'train'/('strong750-'+v+'-support-coordinates-v128')/'update_000100.pth';sha=hashlib.sha256(p.read_bytes()).hexdigest();assert all(e['weight_sha256']==sha for e in entries if '-'+v+'-' in e['name']);p.with_suffix('.sha256').write_text(sha+'  '+p.name+'\n');weights.append(dict(path=str(p.relative_to(R)),sha256=sha,bytes=p.stat().st_size))
(D/'support-coordinate-weight-recovery-v136.json').write_text(json.dumps(dict(weights=weights,scope='Full model/Adam/RNG checkpoint recovered; scientific outcomes separate'),indent=2))
record('support_coordinate_native_v130_all_closed',evidence='research/support-pressure-20261003/support-coordinate-native-v130-results.json',config={'actual_episodes':8,'weights':weights},conclusion=receipt['conclusion'],next='Freeze750/staged path, then exactly4 new independentcontinuouscases; one restoredstartup and newRelease.',state_updates={'active_remote_native_launcher_pids':[],'active_remote_training_launcher_pids':[]})
print(json.dumps(receipt))
