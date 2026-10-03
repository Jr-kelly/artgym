"""Real hardware samples only; missing pre-monitor history is not reconstructed."""
import datetime,json,os,pathlib,subprocess,time
R=pathlib.Path(__file__).resolve().parents[2];out=R/'runs/antirotation-grasp-20261004/resources';out.mkdir(parents=True,exist_ok=True)
(out/'monitor-identity.json').write_text(json.dumps({'pid':os.getpid(),'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'interval_s':15,'scope':'Instantaneous nvidia-smi samples, not complete pre-start utilization history'},indent=2))
while True:
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result=subprocess.run(['nvidia-smi','--query-gpu=index,uuid,utilization.gpu,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True)
    rows=[]
    if result.returncode==0:
        for line in result.stdout.splitlines():
            index,uuid,util,memory=[v.strip() for v in line.split(',')]
            rows.append(dict(index=int(index),uuid=uuid,utilization_percent=float(util),memory_MiB=float(memory)))
    row=dict(utc=utc,gpus=rows,whole_machine_sample_mean_percent=sum(x['utilization_percent'] for x in rows)/len(rows) if rows else None,exit_code=result.returncode)
    with (out/'actual-utilization-samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    time.sleep(15)
