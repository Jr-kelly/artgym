"""Acquire a new ring back bearing while retaining all three actual old clamps."""
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);src=Path('runs/flat-table-20261006/direct/recorded/fresh-widthflip-v877-actual-end-v880');z=np.load(src/'takeover.npz');r=json.loads(Path('runs/flat-table-20261006/direct/preparation/acquired-ring-back-bearing-v888/result.json').read_text());assert r['geometry_pass'];f=FunctionalEntryAffordance();L=np.array(r['wrist_in_knife']);h=np.array(r['hand_q']);V=np.concatenate([v for v,_ in f.g.meshes['hand_r_ring_pad_link']]);kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp'])
 def foot(q):
  T=L@f.g.w.forward(q)['hand_r_ring_pad_link'];P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,1]-P[:,1].max())/.0002);return w@P/w.sum()
 J=np.empty((3,4))
 for j,k in enumerate(range(12,16)):
  up=h.copy();dn=h.copy();up[k]+=1e-5;dn[k]-=1e-5;J[:,j]=(foot(up)-foot(dn))/2e-5
 initial=z['issued_target'].astype(float);target=initial.copy();target[19:23]=h[12:16]+J.T@np.array([0,.2,0])/kp[12:16];assert np.minimum(target[7:]-f.g.w.lower,f.g.w.upper-target[7:]).min()>0;rows=[]
 for time in np.arange(0,4.5+1/30,1/30):
  u=np.clip(time/3,0,1);u=u**3*(10-15*u+6*u*u);q=initial+(target-initial)*u;rows.append(dict(time_s=float(time),arm_q=q[:7].tolist(),hand_q=q[7:].tolist()))
 motor=a.output/'motor.json';motor.write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.04,scope=__doc__),indent=2));cmd=json.loads(Path('runs/flat-table-20261006/direct/development/actual-widthflip-restoration-hold-v881/command.json').read_text());cmd[0]=sys.executable
 for flag,value in [('--seconds','4.5'),('--recorded-support-command',str(motor)),('--output',str(a.output/'simulation'))]:cmd[cmd.index(flag)+1]=value
 if '--video'not in cmd:cmd.append('--video')
 (a.output/'command.json').write_text(json.dumps(cmd,indent=2));record('new_ring_bearing_actual_acquisition_started_v890',[str(a.output/'command.json')],dict(scope=__doc__,new_ring_normal_preload_proxy_N=.2,old_three_targets='unchangedactualcapturedissued',source='actual877 end, missingrobotvelocity/cache',normal_preload_q_delta=(target[19:23]-h[12:16]).tolist()),updates={'add_active_jobs':[str(a.output)]},next_step='NativeRingcontact mustcarrybeforeoldThumbrelease; fail->inspectbearingtransfer mechanism, no individualtracker/pressuregrid')
 try:subprocess.run(cmd,check=True)
 finally:record('new_ring_bearing_actual_acquisition_terminal_v890',[str(a.output/'simulation')],updates={'remove_active_jobs':[str(a.output)]},next_step='ActualRingcontactduration/nativegeometry/carry/H verifynewbearing thenpartialthumbunload')
if __name__=='__main__':main()
