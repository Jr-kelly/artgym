"""Refresh persistent round budget from immutable launch and terminal records."""
import datetime,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'runs/g2-functional-v2-20260928'
def main():
 state=json.loads((BASE/'state.json').read_text());items=[];gpu=0.;reserved=0.;learning=set();controls=0
 for path in sorted(BASE.glob('*-launch.json')):
  m=json.loads(path.read_text());terminal=BASE/(m['name']+'-status.json');running=BASE/(m['name']+'-running.json')
  pid=json.loads(running.read_text())['pid'] if running.exists() else None
  command=Path('/proc')/str(pid)/'cmdline';cmd=command.read_bytes().decode(errors='replace').replace('\x00',' ') if command.exists() else ''
  live=bool(cmd and (m['name'] in cmd or '-m '+m['command'][3] in cmd))
  if terminal.exists():s=json.loads(terminal.read_text());gpu+=s['seconds']/3600
  else:s={};reserved+=m['max_seconds']/3600
  if m['kind']=='learning':learning.add(m.get('learning_config',m['name']))
  else:controls+=1
  items.append(dict(name=m['name'],pid=pid,verified_live=live,exit_code=s.get('exit_code'),kind=m['kind'],source_version=m['source_version']))
 state.update(last_audit_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_started=controls,learning_started=len(learning),learning_configurations=sorted(learning),conservative_gpu_hours_completed=gpu,conservative_gpu_hours_reserved=reserved,verified_processes=items)
 (BASE/'state.json').write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps({k:state[k] for k in ['last_audit_utc','control_started','learning_started','conservative_gpu_hours_completed','conservative_gpu_hours_reserved']}))
 print(json.dumps(dict(active=[r for r in items if r['verified_live']])))
if __name__=='__main__':main()
