"""Copy completed outputs while GPU queue continues; archive each fixed geometry/protocol."""
import json,os,shlex,subprocess,time
from scripts.record_wuji_width_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']);env=host_tool_environment();seen=set();deadline=time.monotonic()+10800
while time.monotonic()<deadline:
 q=json.loads((D/'queues/frozen-final-resume-v2.json').read_text());done=[t for t in q['tasks'] if t['status']=='complete' and t['name'] not in seen]
 if done:
  subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*['wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/./'+t['output'] for t in done],str(R)+'/'],env=env,check=True,timeout=1200)
  seen.update(t['name'] for t in done)
  (D/'FINAL_INCREMENTAL_FETCH.json').write_text(json.dumps(dict(completed_copied=sorted(seen),count=len(seen)),indent=2)+'\n')
 for g in ['baseline','W110','W120','W115','W115_T110']:
  for protocol in ['F','S2','S5']:
   group=[t for t in q['tasks'] if t['geometry']==g and t['identity']['protocol']==protocol];name='width-final-'+g+'-'+protocol+'-raw-v2'
   if len(group)==6 and all(t['name'] in seen for t in group) and not (R/'delivery/width-student-distillation-20261002'/ (name+'.tar.gz')).exists():
    subprocess.run(['python3','-m','scripts.archive_wuji_width','--name',name,'--paths',*[t['output'] for t in group]],cwd=R,check=True)
 if len(seen)==90:break
 if any(t['status']=='failed' for t in q['tasks']) and not any(t['status']=='running' for t in q['tasks']):break
 time.sleep(20)
record('final_incremental_copy_and_archival_finished',evidence='research/width-student-distillation-20261002/FINAL_INCREMENTAL_FETCH.json',copied=len(seen),next='Complete independent rescore and publication')
