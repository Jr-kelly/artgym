"""Read the current authorized endpoint; failure receipts omit authentication."""
import argparse
import datetime
import json
import os
import subprocess
from pathlib import Path
from scripts.record_wuji_width_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment


PROBE = r'''
import csv,json,os,pathlib,platform,subprocess,shutil,sys
def command(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
 return dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
out=dict(hostname=platform.node(),utc=command(['date','-u','+%FT%TZ'])['stdout'].strip(),
 cpu_count=os.cpu_count(),memory=pathlib.Path('/proc/meminfo').read_text(),disk_tmp=dict(zip(['total','used','free'],shutil.disk_usage('/tmp'))),
 gpu=command(['nvidia-smi','--query-gpu=index,uuid,name,utilization.gpu,memory.used,driver_version','--format=csv,noheader,nounits']),
 compute=command(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader']),
 runtime_path='/tmp/wuji-student-runtime/bin/python')
for label,root in [('geometry','/tmp/artgym-geometry-20261002'),('width','/tmp/artgym-width-20261002')]:
 root=pathlib.Path(root);d=root/'research'/('geometry-generalization-20261002' if label=='geometry' else 'width-student-distillation-20261002')
 if (d/'STATE.json').exists():out[label+'_state']=json.loads((d/'STATE.json').read_text())
 out[label+'_active_receipts']=[json.loads(p.read_text()) for p in (root/'runs'/d.name/'jobs').glob('*/identity.json') if not (p.parent/'result.json').exists()]
 out[label+'_active_executions']=[json.loads(p.read_text()) for p in (root/'runs'/d.name/'jobs').glob('*/execution.json') if json.loads(p.read_text()).get('status')!='finished']
 for name in ['AGENTS.md','WUJI_GOAL_HANDOFF.md']:
  p=root/name
  if p.exists():out[label+'_'+name]=p.read_text()[:12000]
runtime=pathlib.Path(out['runtime_path'])
if runtime.exists():
 env=os.environ.copy();env['LD_LIBRARY_PATH']=str(runtime.parents[1]/'lib');env['PYTHONNOUSERSITE']='1'
 probe="import isaacgym;import torch,numpy,scipy,sys,json;print(json.dumps(dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,numpy=numpy.__version__,scipy=scipy.__version__,isaacgym=isaacgym.__file__,cuda_available=torch.cuda.is_available())))"
 p=subprocess.run([str(runtime),'-c',probe],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
 out['runtime']=dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
print(json.dumps(out))
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
    assert ssh[0]=='ssh' and 'wangjiarui@10.13.160.5' in ssh and '33024' in ssh
    import shlex
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result=subprocess.run(ssh+['python3 -c '+shlex.quote(PROBE)],capture_output=True,text=True,timeout=60,env=host_tool_environment())
        if result.returncode:
            # stderr from transport only; do not serialize the private SSH argv.
            reason=('Connection timed out' if 'timed out' in result.stderr else
                    'Authentication failed' if 'Permission denied' in result.stderr else 'SSH transport/host-key failure')
            report=dict(utc=now,connected=False,exit_code=result.returncode,error=reason)
        else:
            report=json.loads(result.stdout);report.update(connected=True,checked_utc=now)
    except subprocess.TimeoutExpired:
        report=dict(utc=now,connected=False,error='SSH/remote inventory timed out at60s')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    if not report['connected']:
        record('authorized_endpoint_inventory_failed',evidence=str(a.output),state_updates=dict(remote_inventory_verified=False),
               next='Keep completed preparation; wait for usable authorized endpoint, then inventory once and resume')
        raise SystemExit(1)
    devices=list(__import__('csv').reader(report['gpu']['stdout'].splitlines()))
    h200=[int(row[0]) for row in devices if 'H200' in row[2]]
    no_active=not any(report[k] for k in ['geometry_active_receipts','width_active_receipts','geometry_active_executions','width_active_executions'])
    local_unknown=[p for p in (R/'runs/width-student-distillation-20261002/jobs').glob('*/result.json') if json.loads(p.read_text()).get('remote_status_unknown')]
    no_active=no_active and not local_unknown
    s=json.loads((D/'STATE.json').read_text())
    prior=report.get('geometry_state',{}).get('cumulative_gpu_hours',s['historical_gpu_hours'])
    assert prior==s['historical_gpu_hours'], 'Reconcile changed remote resource ledger before launch'
    # Any interrupted new job must be recovered by identity, not rerun.
    record('authorized_remote_inventory_read',evidence=str(a.output),actual_h200_count=len(h200),
           state_updates=dict(remote_inventory_verified=True,remote_additional_consumption_unknown=not no_active,actual_h200_indices=h200),
           next='Read remote AGENTS/current tasks, reconcile any active receipts, restore only missing compatible runtime and pinned inputs; no job preemption')


if __name__=='__main__':main()
