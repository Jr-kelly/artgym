"""Evaluation-only loaded contact footprint and actual normal-force distribution."""
import argparse,json
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 windows=[(14.3,16),(16,21),(21,26),(26,31),(31,36)];stats=[{} for _ in windows];counts=np.zeros(len(windows),int)
 for line in (a.trial/'wrap-contact-physical-steps.jsonl').open():
  d=json.loads(line)
  for i,(lo,hi) in enumerate(windows):
   if not lo<=d['time_s']<hi:continue
   counts[i]+=1
   for c in d['contacts']:
    if c['normal_magnitude_N']<=0:continue
    finger=c['hand_link'].split('_')[2];key=finger+':'+c['knife_link'];r=stats[i].setdefault(key,dict(force=0.,point=np.zeros(3),moment=np.zeros(3),front=0.))
    n=c['normal_magnitude_N'];r['force']+=n;r['point']+=n*np.array(c['position_knife_m']);r['moment']+=np.array(c['normal_moment_about_body_origin_Nm']);r['front']+=n*(c.get('authored_pad_front_axis_normal_force_cosine') or 0.)
 rows=[]
 for count,window,stats in zip(counts,windows,stats):
  rows.append(dict(window_s=window,samples=int(count),contacts={key:dict(mean_normal_N=r['force']/max(count,1),weighted_position_knife_mm=(r['point']/r['force']*1000).tolist(),mean_normal_moment_Nm=(r['moment']/max(count,1)).tolist(),weighted_front_cosine=r['front']/r['force']) for key,r in stats.items()}))
 result=dict(trial=str(a.trial),scope=__doc__,axial_total_contact_force_N=None,rows=rows);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
