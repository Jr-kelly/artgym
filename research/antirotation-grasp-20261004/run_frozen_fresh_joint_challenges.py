"""Freeze by declared development gates, then open exactly four fresh cases."""
import hashlib,json,subprocess,time
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=Path('research/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
def wait_file(path):
    while not path.exists():time.sleep(5)
    return json.loads(path.read_text())
# No physical fresh-case result is read here. Both contrasts receive identical
# declared two development tests; .04 is preferred only if both qualify.
choices=[]
for label,versions,version in [('range04',['v32','v33'],'v8'),('range12',['v34','v35'],'v9')]:
    results=[]
    for kind,v in zip(['nominal','thin'],versions):
        results.append(wait_file(B/'continuous'/('actual-table-'+kind+'-table-prior-'+label+'-frozen50-load2-'+v)/'functional-evaluation.json'))
    name='strict16-table-prior-closure-longhorizon-'+label+'-reset750-'+version
    choices.append(dict(label=label,checkpoint=str(B/'train'/name/'update_000050.pth'),qualified=all(r['continuous_pickup_demo_pass'] for r in results),development_trace_hashes=[r['trace_sha256'] for r in results]))
selected=next((r for r in choices if r['qualified']),None)
checkpoint=Path(selected['checkpoint']) if selected else Path('runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth')
freeze=dict(utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),selection_rule='Both nominal and thin actual full continuous functional checks must pass; .04 preferred if both ranges qualify; otherwise unchanged750. No fresh outcomes available before selection.',candidates=choices,selected_label=selected['label'] if selected else 'unchanged750',checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),takeover_seconds=5 if selected else 16,scope='Current-round fresh joint-conditions simulation only; no realhardware/cross-model claim')
(D/'FRESH-JOINT-ACTOR-FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n');record('fresh_joint_validation_actor_frozen',config=freeze,evidence=str(D/'FRESH-JOINT-ACTOR-FREEZE.json'),next='Open exactly four preregistered cases once; count geometry rejection/failure, no reroll or outcome-driven repair')
rows=wait_file(B/'common-joint-reserve-repair-v2/fresh-corrected-outcomes.json');assert len(rows)==4
O=B/'fresh-joint-validation4-v1';O.mkdir(exist_ok=False);outcomes=[]
base=json.loads((B/'jobs/actual-table-projected-grasp-frozen750-load2-v17/identity.json').read_text())['command']
for i,row in enumerate(rows):
    if not row['geometry_passed']:
        outcomes.append(dict(case=i,status='geometry-rejected',functional_pass=False,evidence=row['directory']));continue
    name='fresh-joint-frozen-case%02d-v1'%i;trial=O/('case%02d'%i);directory=Path(row['directory']);c=row['condition'];cmd=list(base)
    replacements={'--output':str(trial),'--grasp-plan':str(directory/'motor-plan.json'),'--residual-checkpoint':str(checkpoint),'--thumb-reference-override':str(directory/'reference.json'),'--load':str(c['load']),'--detent':str(c['detent'])}
    for flag,value in replacements.items():cmd[cmd.index(flag)+1]=value
    cmd+=['--knife-asset',row['asset'],'--load-profile',c['profile'],'--load-frequency',str(c['frequency']),'--actuation-delay-frames',str(c['delay']),'--observation-noise',str(c['noise']),'--observation-bias',str(c['bias']),'--seed',str(2026100467+i),'--takeover-seconds',str(freeze['takeover_seconds'])]
    record('fresh_joint_frozen_case_started',config={'case':i,'condition':c,'checkpoint_sha256':freeze['checkpoint_sha256'],'asset_sha256':row['asset_sha256'],'scope':'First andonly fresh behavioralrun; physicalasset separatefromlegal onceinitialestimate'},evidence=str(trial),next='Preserve actual fulltrace/video includingfailures, unchangedcriterion; no resultdrivenrepair')
    code=subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--']+cmd).returncode
    if code==0:
        code=subprocess.run([PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]).returncode
    result=json.loads((trial/'functional-evaluation.json').read_text()) if code==0 else None
    outcomes.append(dict(case=i,status='evaluated' if result else 'execution-failed',functional_pass=bool(result and result['continuous_pickup_demo_pass']),condition=c,asset_sha256=row['asset_sha256'],evidence=str(trial),result=result))
    (O/'outcomes.json').write_text(json.dumps(dict(freeze=freeze,rows=outcomes),indent=2));record('fresh_joint_frozen_case_closed',config=outcomes[-1],evidence=str(trial),next='Nextpredeclaredcase only; no repeats/retuning')
(O/'outcomes.json').write_text(json.dumps(dict(freeze=freeze,rows=outcomes),indent=2));record('fresh_joint_frozen_validation_closed',config={'cases':4,'functional_passes':sum(r['functional_pass'] for r in outcomes),'scope':'All preregisteredcurrent-roundjointcases retained; fourcases alone cannotestablishwidegeneralization/hardware'},evidence=str(O/'outcomes.json'),next='Reportremainingblocks andpackageexactcode/weights/config/fullvideos/failures/recoveryevidence',state_updates={'fresh_joint_validation_pipeline_pid':None})
