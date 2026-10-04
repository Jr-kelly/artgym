"""Export aligned diagnostic force/position curves and observed motion onsets.

The series device changes slider dynamics. Its calibrated external cap force
is attributable to the thumb only at the validity samples from the analyzer.
Motion onset is a kinematic observation, not a measured passive brake reaction.
"""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args()
 data=np.load(a.trial/'diagnostic-axial-aligned.npz');t=data['time_s'];valid=data['valid'];force=data['diagnostic_axial_signed_N'];velocity=data['velocity_m_s'];rows=[]
 for name,start,direction in [('extend1',16,1),('return1',21,-1),('extend2',26,1),('return2',31,-1)]:
  window=(t>=start)&(t<start+5);moving=window&valid&(direction*velocity>.001)
  # Require 50ms of continuous direction-matched moving samples. Retain the
  # declared rule for all directions and do not tune it to individual results.
  step=float(np.median(np.diff(t)));n=max(1,int(np.ceil(.05/step)));runs=np.convolve(moving.astype(int),np.ones(n,dtype=int),mode='valid');ids=np.flatnonzero(runs==n);onset=float(t[ids[0]]) if ids.size else None
  before=(window&valid&(t<=onset)&(t>=onset-.5)) if onset is not None else np.zeros_like(valid)
  rows.append(dict(phase=name,motion_onset_time_s=onset,criterion='Guide velocity in commanded direction >1mm/s continuously for50ms, valid thumb-only samples',pre_onset_500ms_directional_force_max_N=float(np.max(direction*force[before])) if before.any() else None,pre_onset_500ms_directional_force_95th_N=float(np.percentile(direction*force[before],95)) if before.any() else None,scope='Single recorded trial of modified series device. Pre-onset maxima can include transient/stall and are not a repeatable breakaway or capacity measurement.'))
 operation=(t>=16)&(t<=36)
 fig,axes=plt.subplots(4,1,figsize=(11,9),sharex=True)
 axes[0].plot(t[operation],np.where(valid,force,np.nan)[operation],lw=.7);axes[0].set_ylabel('Signed axial force (N)');axes[0].axhline(0,color='k',lw=.5)
 axes[1].plot(t[operation],data['pressure_normal_N'][operation],lw=.8);axes[1].set_ylabel('Normal pressure (N)')
 axes[2].plot(t[operation],data['rail_guide_position_m'][operation]*1000,label='guide');axes[2].plot(t[operation],data['diagnostic_cap_position_m'][operation]*1000,label='cap',alpha=.6);axes[2].set_ylabel('Position above stop (mm)');axes[2].legend()
 axes[3].plot(t[operation],velocity[operation]*1000,lw=.8);axes[3].set_ylabel('Guide velocity (mm/s)');axes[3].set_xlabel('Simulation / video time (s)')
 for ax in axes:
  ax.set_xlim(16,36);ax.grid(alpha=.2)
  for clock in [16,21,26,31]:ax.axvline(clock,color='gray',lw=.5)
 fig.suptitle('Modified calibrated series diagnostic; axial sign + = extension\nNormal pressure interpolated from 30Hz trace; axial/guide samples 960Hz. Not original-scene or hardware force.')
 fig.tight_layout();fig.savefig(a.trial/'diagnostic-axial-curves.png',dpi=160);fig.savefig(a.trial/'diagnostic-axial-curves.pdf');plt.close(fig)
 (a.trial/'diagnostic-motion-onsets.json').write_text(json.dumps(dict(scope=__doc__,rows=rows),indent=2)+'\n')
 print(json.dumps(rows))

if __name__=='__main__':main()
