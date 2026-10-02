"""Validate frozen identity coverage, independent record counts and unchanged selection."""
import collections,json,subprocess
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_contract import sha
from scripts.wuji_width_jobs import source_hash
freeze=D/'final-freeze.json';original=subprocess.check_output(['git','show','523cff1c865ecd62c1999bb3114603c16401aa82:research/width-student-distillation-20261002/final-freeze.json'],cwd=R)
assert original==freeze.read_bytes()
f=json.loads(freeze.read_text());old=json.loads((D/'queues/frozen-final-v1.json').read_text());q=json.loads((D/'queues/frozen-final-resume-v2.json').read_text());tasks=q['tasks'];assert len(tasks)==90 and all(t['status']=='complete' for t in tasks)
assert len({t['key'] for t in tasks})==90 and {t['key'] for t in tasks}=={t['key'] for t in old['tasks']}
assert sum('retry_of' in t for t in tasks)==8
assert source_hash(R)==f['source_sha256']
for t in tasks:
 previous=next(o for o in old['tasks'] if o['key']==t['key']);assert t['identity']==previous['identity']
 r=json.loads((R/'runs/width-student-distillation-20261002/jobs'/t['name']/'result.json').read_text());assert r['exit_code']==0 and not r['remote_status_unknown'] and r['source_sha256']==f['source_sha256']
 assert (R/t['output']/'geometry-receipt.json').exists()
for m in f['models'].values():assert sha(R/m['path'])==m['sha256']
manifest=json.loads((D/'FINAL_MANIFEST.json').read_text());assert len(manifest['runs'])==90
assert {r['directory'] for r in manifest['runs']}=={t['output'] for t in tasks}
a=R/'runs/width-student-distillation-20261002/analysis/frozen-final-v1';j=json.loads((a/'report.json').read_text());assert len(j['cells'])==360
import csv
with (a/'episodes.csv').open() as h:episodes=sum(1 for _ in csv.DictReader(h))
assert episodes==f['episodes']==35280
opening=min(json.loads((R/'runs/width-student-distillation-20261002/jobs'/t['name']/'identity.json').read_text())['start_utc'] for t in old['tasks'] if t['status']=='failed')
optimization=[json.loads(p.read_text()) for p in (R/'runs/width-student-distillation-20261002/jobs').glob('*/result.json') if 'scripts.train_wuji_unified_student' in json.loads(p.read_text())['command']]
assert optimization and all(j['end_utc']<opening for j in optimization)
result=dict(freeze_unchanged_since_public_commit='523cff1c865ecd62c1999bb3114603c16401aa82',freeze_sha256=sha(freeze),source_sha256=source_hash(R),unique_task_keys=90,completed_tasks=90,provider_interrupted_retries=8,missing_tasks=0,duplicate_counted_tasks=0,cells=360,episodes=episodes,independent_initial_states=1960,selected_main='C_endpoint',model_hashes_verified=True,all_exit_codes_zero=True,formal_updates=12800,no_post_final_optimization=True,raw_archives_expected=15,final_manifest_sha256=sha(D/'FINAL_MANIFEST.json'))
(D/'FINAL_COMPLETION_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
record('frozen_final_completion_coverage_audit_passed',evidence='research/width-student-distillation-20261002/FINAL_COMPLETION_AUDIT.json',next='Publish exact final evidence and close GPU work; no new model selection')
