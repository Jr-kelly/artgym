"""Retrieve two new remote snapshots, then execute predeclared development gates."""
import hashlib,json,subprocess,time
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=Path('research/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';REMOTE='/home/wangjiarui/artgym-antirotation-necessary24-20261004';SSH=['ssh','-p','33024','-o','BatchMode=yes','-o','ConnectTimeout=10','wangjiarui@10.13.160.5'];O=B/'necessary24-frozen25-development-v1';O.mkdir(exist_ok=False);rows=[]
for kind in ['frozen-thumb','joint']:
    name='necessary24-retained750-'+kind+'-frozen25-v3';job=B/'jobs'/name;train=B/'train'/name
    while True:
        program='from pathlib import Path\nimport json,hashlib\nr=Path('+repr(REMOTE)+')\np=r/'+repr(str(job/'result.json'))+'\nif p.exists():\n j=json.loads(p.read_text());w=r/'+repr(str(train/'update_000025.pth'))+'\n print(json.dumps(dict(result=j,weight_sha256=hashlib.sha256(w.read_bytes()).hexdigest() if w.exists() else None)))\n'
        reply=subprocess.run(SSH+['python3','-'],input=program,text=True,capture_output=True,timeout=30)
        if reply.returncode==0 and reply.stdout.strip():receipt=json.loads(reply.stdout);break
        time.sleep(20)
    for directory in [job,train]:
        directory.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['rsync','-a','-e','ssh -p33024 -o BatchMode=yes -o ConnectTimeout=10','wangjiarui@10.13.160.5:'+REMOTE+'/'+str(directory)+'/',str(directory)+'/'],check=True,timeout=60)
    record('necessary24_remote_train_closed',closed_job={'name':name,'machine':'10.13.160.5:33024'},config={'kind':kind,'result':receipt['result'],'weight_sha256':receipt['weight_sha256']},evidence=str(job/'result.json'),next='Oneeach predeclared nominal/thin/height4 development; no use of priorfreshcases or training successrate for promotion')
    assert receipt['result']['exit_code']==0, 'Preserve remote failure before claiming a frozen model'
    weight=train/'update_000025.pth';assert hashlib.sha256(weight.read_bytes()).hexdigest()==receipt['weight_sha256']
    checks=[]
    for case,source in [('nominal',B/'jobs/actual-table-projected-grasp-frozen750-load2-v17/identity.json'),('thin',B/'jobs/actual-table-thin-allcontact-frozen750-load2-v24/identity.json'),('height4',B/'jobs/height-development-unchanged750-case01-v1/identity.json')]:
        trial=O/(kind+'-'+case);cmd=json.loads(source.read_text())['command'];cmd[0]=PY;cmd[cmd.index('--output')+1]=str(trial);cmd[cmd.index('--residual-checkpoint')+1]=str(weight)
        record('necessary24_frozen25_development_started',config={'kind':kind,'case':case,'weight_sha256':receipt['weight_sha256'],'scope':'Knowntrainingmorphology development, onefull36s nativeepisode, originalcriterion; notindependentfresh orhardware'},evidence=str(trial),next='Checkfulltwo-cyclebehavior once, preservefailureandvideo')
        subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name','necessary24-frozen25-'+kind+'-'+case+'-v1','--']+cmd,check=True)
        subprocess.run([PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)],check=True)
        result=json.loads((trial/'functional-evaluation.json').read_text());checks.append({'case':case,'trial':str(trial),'result':result});record('necessary24_frozen25_development_closed',config={'kind':kind,'case':case,'result':result},evidence=str(trial),next='Completepredeclared gates without repeat/thresholdtuning')
    rows.append({'kind':kind,'weight_sha256':receipt['weight_sha256'],'checks':checks,'all_three_functional_pass':all(c['result']['continuous_pickup_demo_pass'] for c in checks)})
    (O/'outcomes.json').write_text(json.dumps({'role':'Knownmorphology frozen25development only; original4fresh750outcomes remainseparate; no independent generalization claim.','rows':rows},indent=2)+'\n')
record('necessary24_preserved_thumb_contrast_closed',config={'rows':rows,'scope':'Fixed25criticalcomparison. Continueonlywithmeaningfulfullcyclegain; no unchanged negativeextension. No newcandidate selected by oldfreshoutcomes.'},evidence=str(O/'outcomes.json'),state_updates={'necessary24_frozen_development_pipeline_pid':None},next='Assesspredeclaredgates andhigherload ifallthreepass; completehonestReleaseafterworkminimum')
