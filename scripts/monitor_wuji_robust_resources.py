"""Small read-only monitor; four-hour averages require four hours of actual data."""
import datetime,json,subprocess,time,os
from pathlib import Path
from scripts.record_wuji_robust_goal import record,D
from scripts.host_tool_environment import host_tool_environment
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-p','33024','wangjiarui@10.13.160.5']
def main():
    record('resource_monitor_started',local_pid=os.getpid(),target='whole-machine H200 mean>40%, rolling4h>27%',evidence='research/robust-knife-family-20261003/resources.jsonl',next='Inspect real utilization and useful throughput; no filler jobs')
    samples=[]
    for _ in range(12*60*4+80):
        now=datetime.datetime.now(datetime.timezone.utc);row=dict(utc=now.isoformat())
        try:
            answer=subprocess.run(SSH+['nvidia-smi --query-gpu=index,uuid,utilization.gpu,memory.used --format=csv,noheader,nounits; nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader,nounits'],capture_output=True,text=True,timeout=25,env=host_tool_environment())
            lines=answer.stdout.splitlines();gpus=[]
            for line in lines[:4]:
                v=[x.strip() for x in line.split(',')]
                if len(v)==4 and v[0].isdigit():gpus.append(dict(index=int(v[0]),uuid=v[1],utilization=int(v[2]),memory_mib=int(v[3])))
            row.update(gpus=gpus,compute_processes=lines[4:],exit=answer.returncode)
            if len(gpus)==4:
                mean=sum(g['utilization'] for g in gpus)/4;samples.append((now.timestamp(),mean));samples=[s for s in samples if s[0]>=now.timestamp()-14400]
                row.update(whole_machine_current_mean=mean,observed_window_seconds=samples[-1][0]-samples[0][0],observed_window_mean=sum(v for _,v in samples)/len(samples),full4h_covered=samples[-1][0]-samples[0][0]>=14385)
        except Exception as e:row['error']=type(e).__name__
        with (D/'resources.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        time.sleep(15)
if __name__=='__main__':main()
