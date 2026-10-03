"""Small signed-direction measurement importer for passive solver-brake capacity.
No robot connection. Synthetic examples are explicitly non-calibration data.
"""
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np

def fit(source,output,synthetic=False):
 output.mkdir(parents=True,exist_ok=False)
 with source.open(newline='') as f:rows=list(csv.DictReader(f))
 if not rows:raise ValueError('No measured rows')
 groups={};pressure_values=set()
 for row in rows:
  direction=row['direction'];assert direction in ['extend','retract']
  x=float(row['position_mm'])/1000;y=float(row['resistance_N']);assert np.isfinite([x,y]).all() and x>=0 and y>=0
  phase=row['phase'];assert phase in ['startup','running']
  pressure=row.get('normal_pressure_N','').strip()
  if pressure:pressure_values.add(float(pressure))
  groups.setdefault(direction,[]).append((x,y,phase))
 if set(groups)!={'extend','retract'}:raise ValueError('Both measured directions required')
 if len(pressure_values)>1:raise ValueError('Separate measured normal-pressure conditions; do not silently pool profiles')
 result=dict(format='wuji-passive-resistance-profile-v1',synthetic_example=synthetic,real_calibration=not synthetic,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),normal_pressure_N=list(pressure_values),directions={},scope='Nonnegative finite zero-velocity solver-brake capacities approximating measured resistance; no positive rail drive, no instantaneous-force or real-upper-bound claim; only interpolate inside recorded support.')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,4))
 for direction,vals in groups.items():
  running=np.array([(x,y) for x,y,phase in vals if phase=='running']);start=[y for _,y,phase in vals if phase=='startup']
  if len(running)<2 or not start:raise ValueError('Each direction needs startup and >=2 running samples')
  xs=np.unique(running[:,0]);ys=np.array([np.median(running[running[:,0]==x,1]) for x in xs]);result['directions'][direction]=dict(position_m=xs.tolist(),capacity_N=ys.tolist(),startup_peak_N=max(start),position_range_m=[float(xs.min()),float(xs.max())],startup_scope='Recorded peak at supplied pressure; future solver integration uses passive capacity, not force command')
  ax.scatter(running[:,0]*1000,running[:,1],s=15,label=direction+' raw');ax.plot(xs*1000,ys,label=direction+' median interpolation')
 ax.set(xlabel='Position from measured fully retracted endpoint (mm)',ylabel='Opposing resistance / model capacity (N)',title='SYNTHETIC EXAMPLE — NOT REAL CALIBRATION' if synthetic else 'Measured data and passive approximation');ax.legend();fig.tight_layout();fig.savefig(output/'raw-versus-model.png',dpi=160);plt.close(fig)
 (output/'profile.json').write_text(json.dumps(result,indent=2)+'\n');return result

def capacity(profile,position,velocity):
 direction='extend' if velocity>1e-5 else 'retract' if velocity< -1e-5 else None
 choices=[profile['directions'][direction]] if direction else list(profile['directions'].values())
 # Near rest choose the larger bidirectional bound, so no direction oracle or positive work is added.
 values=[]
 for row in choices:
  lo,hi=row['position_range_m']
  if not lo<=position<=hi:raise ValueError('Position outside measured profile support')
  value=float(np.interp(position,row['position_m'],row['capacity_N']))
  if abs(velocity)<.002:value=max(value,row['startup_peak_N'])
  values.append(value)
 return max(values)

def main():
 p=argparse.ArgumentParser();p.add_argument('--csv',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--synthetic-example',action='store_true');a=p.parse_args();print(json.dumps(fit(a.csv,a.output,a.synthetic_example)))
if __name__=='__main__':main()
