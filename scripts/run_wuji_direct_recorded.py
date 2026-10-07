"""Short actual-state development runner, never a full-route acceptance."""
import argparse,json,subprocess,sys
from pathlib import Path
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--motor',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,required=True);p.add_argument('--uncertainty',required=True);p.add_argument('--decision',required=True);p.add_argument('--close-camera-direction',type=float,nargs=3,default=[.05,-.35,.65]);p.add_argument('--support-camera-direction',type=float,nargs=3);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
c=json.load(open('runs/flat-table-20261006/direct/development/center-load-feedback-v8/command.json'));c[0]=sys.executable
i=c.index('--flat-table-prefix');del c[i:i+2]
c[c.index('--seconds')+1]=str(a.seconds);c[c.index('--output')+1]=str(a.output/'simulation');c+=['--recorded-handoff',str(a.source),'--recorded-support-command',str(a.motor),'--close-camera-direction']+[str(x) for x in a.close_camera_direction]
if a.support_camera_direction:c+=['--support-camera-direction']+[str(x) for x in a.support_camera_direction]
(a.output/'command.json').write_text(json.dumps(c,indent=2));record('direct_recorded_native_start',[str(a.output/'command.json'),str(a.motor)],config={'uncertainty':a.uncertainty,'decision':a.decision,'seconds':a.seconds,'scope':'Short actualstate development; missing exactrobotvelocity/contactcache; no final acceptance'},updates={'active_jobs':[str(a.output)]},next_step=a.decision)
try:subprocess.run(c,check=True)
finally:record('direct_recorded_native_terminal',[str(a.output/'simulation')],updates={'active_jobs':[]},next_step='Read actual contacts and first divergence, advance changed mechanism without fullpickup rerun')
