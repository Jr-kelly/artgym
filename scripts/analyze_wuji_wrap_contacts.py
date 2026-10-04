"""Actual per-link normal distribution and first/second-cycle contact continuity; not force area."""
import argparse,json
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();windows=[('initial_hold',14,16),('extend1',16,21),('return1',21,26),('extend2',26,31),('return2',31,36.001)];data=[json.loads(line) for line in (a.trial/'wrap-contact-physical-steps.jsonl').open()];out=[]
 for label,lo,hi in windows:
  z=[r for r in data if lo<=r['time_s']<hi];links=sorted({c['hand_link'] for r in z for c in r['contacts'] if c['knife_link']=='link_0'})
  for link in links:
   series=[];points=[];weights=[];moments=[];under=[]
   for r in z:
    cs=[c for c in r['contacts'] if c['hand_link']==link and c['knife_link']=='link_0'];series.append(sum(c['normal_magnitude_N'] for c in cs));moments.append(np.sum([c['normal_moment_about_body_origin_Nm'] for c in cs],axis=0) if cs else np.zeros(3));under.append(sum(max(0,c['force_normal_contribution_knife_N'][1]) for c in cs if c['position_knife_m'][1]<-.0024))
    for c in cs:points.append(c['position_knife_m']);weights.append(c['normal_magnitude_N'])
   lost=np.array(series)<=1e-6;longest=seq=0
   for v in lost:seq=seq+1 if v else 0;longest=max(seq,longest)
   rate=len(z)/(hi-lo);out.append(dict(phase=label,link=link,contact_fraction=float((~lost).mean()),normal_magnitude_mean_N=float(np.mean(series)),underside_normal_mean_N=float(np.mean(under)),normal_moment_mean_Nm=np.mean(moments,axis=0).tolist(),contact_force_weighted_position_knife_m=np.average(points,weights=weights,axis=0).tolist(),contact_axial_position_range_m=[float(np.min(np.array(points)[:,2])),float(np.max(np.array(points)[:,2]))],longest_zero_contact_seconds=longest/rate))
 result=dict(trial=str(a.trial),scope='Solver normal contributions and actual link/point distribution only; count/span not real contact area, no total axialfriction/constantforce claim.',rows=out);(a.trial/'wrap-contact-analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
