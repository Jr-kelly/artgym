"""Read-only late delivery monitor; bound sampling gaps as zero for the utilization floor."""
import pathlib,json,datetime,subprocess,time,os
from scripts.record_wuji_robust_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-p','33024','wangjiarui@10.13.160.5'];end=datetime.datetime(2026,10,3,7,5,tzinfo=datetime.timezone.utc)
def bound(rows,t):
 pts=[(datetime.datetime.fromisoformat(r['utc']).timestamp(),r['whole_machine_current_mean']) for r in rows if 'whole_machine_current_mean' in r];pts=sorted(pts);low=t-14400;total=0.;covered=0.;maxgap=0.
 for (a,u),(b,_) in zip(pts,pts[1:]):
  if b<low or a>t:continue
  duration=max(0,min(b,t)-max(a,low));maxgap=max(maxgap,b-a)
  observed=duration if b-a<=45 else 0.;covered+=observed;total+=u*observed
 return {'rolling4h_conservative_lower_bound_percent':total/14400,'rolling4h_observed_seconds':covered,'rolling4h_missing_seconds':14400-covered,'max_sample_gap_seconds_in_window':maxgap,'scope':'Timeweighted rectangles only where consecutive samples<=45s. All larger gaps and unsampled tails treated as0 for conservative floor, not imputed utilization.'}
record('late_delivery_resource_monitor_started_after_parent_interruption',local_pid=os.getpid(),config={'period_s':15,'end_utc':end.isoformat(),'previous_pid_absent':2626133},next='Read-only monitor; preserve historical samples and report conservative zero-gap bound, no dummy GPU work')
while datetime.datetime.now(datetime.timezone.utc)<end:
 now=datetime.datetime.now(datetime.timezone.utc);p=subprocess.run(ssh+['nvidia-smi --query-gpu=index,uuid,utilization.gpu,memory.used --format=csv,noheader,nounits; nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader,nounits'],capture_output=True,text=True,timeout=25,env=host_tool_environment());lines=p.stdout.splitlines();gpus=[]
 for line in lines[:4]:
  values=[x.strip() for x in line.split(',')]
  if len(values)==4 and values[0].isdigit():gpus.append({'index':int(values[0]),'uuid':values[1],'utilization':int(values[2]),'memory_mib':int(values[3])})
 row={'utc':now.isoformat(),'gpus':gpus,'compute_processes':lines[4:],'exit':p.returncode}
 if len(gpus)==4:
  row['whole_machine_current_mean']=sum(x['utilization'] for x in gpus)/4;old=[json.loads(x) for x in (D/'resources.jsonl').read_text().splitlines()];row.update(bound(old+[row],now.timestamp()))
 with (D/'resources.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 time.sleep(15)
