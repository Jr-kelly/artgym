"""Summarize measured-scale assumptions and isolated fixture evidence."""
import json
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.wuji_newknife_resistance import capacity,REFERENCE_N
R=Path('research/newknife-20261005');B=Path('runs/newknife-20261005/calibration')
fig,axes=plt.subplots(1,3,figsize=(15,4))
x=np.linspace(0,.04,201)
for kind in ['constant','variable']:
 profile=json.loads((R/f'resistance-{kind}.json').read_text())
 for v,label in [(0,'rest'),(.01,'forward'),(-.01,'return')]:
  if kind=='constant' and v!=0:continue
  axes[0].plot(x*1000,[capacity(profile,q,v) for q in x],label=kind+' '+label)
axes[0].set(xlabel='Position relative initial (mm)',ylabel='Configured passive capacity (N)',title='User75gf constrains scale; curves assumed');axes[0].legend(fontsize=8)
raw=json.loads((B/'reference-v2/raw.json').read_text())
for row in raw[1:6]:axes[1].plot([r['t'] for r in row['samples']],[r['q']*1000 for r in row['samples']],label=str(row['external_known_force_N'])+' N')
axes[1].set(xlabel='Fixture time (s)',ylabel='Actual displacement (mm)',title='Known axial loading / fixed body');axes[1].legend(fontsize=8)
for row in json.loads((B/'profiles-v1/raw.json').read_text())[:2]:axes[2].plot([r['t'] for r in row['rows']],[(r['q_rel_m']-row['initial_q_m'])*1000 for r in row['rows']],label='direction '+str(row['direction']))
axes[2].set(xlabel='Fixture time (s)',ylabel='Actual displacement (mm)',title='Low excess force: +/-0.7365 N');axes[2].legend()
for ax in axes:ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(R/'resistance-calibration.png',dpi=150);plt.close(fig)
result=dict(user_evidence=dict(mass_equivalent_gf=75,converted_N=REFERENCE_N,not_measured=['fulltravel_curve','startup_vs_running','return_direction','normal_pressure_effect']),model=dict(reference='constantcapacity0.73549875N,zero-velocitynativebrake,damping25000Ns/m',variable='reference is forward running mean; +/-8% sinusoidal position variation; return factor0.90; near-rest1.12reference; all curve shapes are assumptions',running_range_N=[REFERENCE_N*.9*.92,REFERENCE_N*1.08],startup_N=REFERENCE_N*1.12),isolated_evidence=dict(reference='runs/newknife-20261005/calibration/reference-v2/summary.json',low_speed='runs/newknife-20261005/calibration/profiles-v1/summary.json:constant cases only',variable='runs/newknife-20261005/calibration/profiles-v3/summary.json',rejected='profiles-v1/v2 variable tests hit endstops; no sustainedforce inference from their endstop portions',near_threshold_motion='known0.7365N ->15.074mm in0.6s in each direction;0.735N remains bounded creep~0.029mm/s'),channels=dict(normal_A='Only later actual handcontact diagnostics',axial_B=None,rail_C=None,robot_axis_force_measured=False),scope='Fixture calibration of passivecapacity in simulation, not realknife curve fit or successful robot task')
(R/'RESISTANCE-CALIBRATION.json').write_text(json.dumps(result,indent=2))
