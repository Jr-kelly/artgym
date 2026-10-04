"""First observation of each necessary height variant, unchanged750, one run."""
import hashlib,json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';rows=json.loads((B/'common-joint-reserve-repair-v2/height-corrected-outcomes.json').read_text());selected=rows[::2];assert len(selected)==4 and len({r['instance_physics_only'] for r in selected})==4;out=B/'height-development-four-v1';out.mkdir(exist_ok=False);base=json.loads((B/'jobs/actual-table-projected-grasp-frozen750-load2-v17/identity.json').read_text())['command'];results=[]
record('necessary_height_first_behavior_preregistered',config={'cases':[r['instance_physics_only'] for r in selected],'observations':'First preregistered observation for eachphysicalvariant, notpickedfrombehavior','checkpoint':'unchanged750','load':.2,'detent':.2,'scope':'Necessaryheight development cases, no candidate selection by outcomes, no freshvalidation reuse'},evidence=str(out),next='Oneactualcontinuous36s/video pervariant, samecriteria; retain failures')
for i,row in enumerate(selected):
    folder=Path(row['output']);name='height-development-unchanged750-case%02d-v1'%i;trial=out/('case%02d'%i)
    if not row['passed']:results.append(dict(case=i,status='geometry-rejected',functional_pass=False));continue
    cmd=list(base)
    for flag,value in {'--output':str(trial),'--grasp-plan':str(folder/'motor-plan.json'),'--thumb-reference-override':str(folder/'reference.json')}.items():cmd[cmd.index(flag)+1]=value
    cmd+=['--knife-asset',str(Path('assets/objects/knife_wuji_antirotation_height_20261004')/row['instance_physics_only']/'mobility.urdf')]
    code=subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--']+cmd).returncode
    if code==0:code=subprocess.run([PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]).returncode
    result=json.loads((trial/'functional-evaluation.json').read_text()) if code==0 else None
    results.append(dict(case=i,instance_physics_only=row['instance_physics_only'],functional_pass=bool(result and result['continuous_pickup_demo_pass']),result=result,evidence=str(trial)))
    (out/'outcomes.json').write_text(json.dumps(results,indent=2));record('necessary_height_first_behavior_closed',config=results[-1],evidence=str(trial),next='Nextpredeclaredvariant only; no geometry/endpointcriterionchanges afterbehavior')
record('necessary_height_four_development_closed',config={'cases':4,'functional_passes':sum(r['functional_pass'] for r in results),'scope':'First known-height development probes, not policywidegeneralization/hardware'},evidence=str(out/'outcomes.json'),state_updates={'height_development_four_pipeline_pid':None},next='Useactualfailuremechanism forfuture meaningfulcurriculum only; complete frozenjointvalidation/recovery/Release')
