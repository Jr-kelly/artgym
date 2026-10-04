"""Recorded body-normal moment and seating drift; tangential forces are absent.

This compares complete physical trials, not planned normals or real contact
area. Normal moment is only one contribution and cannot explain net torque or
establish causality without missing friction/rail/other terms.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 B=Path('runs/wrap-force-20261004');cases=[('Selected V12',B/'continuous/index-wrap-v8-direct-corner-mass-corrected-v4'),('Wide face V24',B/'validation/wrap-wide-face-nominal-v24r2'),('Multi-region V27',B/'validation/wrap-wide-face-multiregion-nominal-v27'),('Post-lift middle V29',B/'validation/wrap-wide-face-postlift-middle-v29r1'),('Reverse reference V30',B/'validation/wrap-wide-face-multiregion-reverse-v30')]
 fig,axes=plt.subplots(4,1,figsize=(14,13),sharex=True);rows=[];colors=plt.cm.tab10(np.arange(len(cases)))
 for (label,path),color in zip(cases,colors):
  trace=np.load(path/'trace.npz');ts=trace['time'];mask=ts>=14;relative=Rotation.from_quat(trace['wrist'][:,3:7]).inv()*Rotation.from_quat(trace['object'][:,3:7]);anchor=relative[np.argmin(abs(ts-16))];rv=(anchor.inv()*relative).as_rotvec();axes[0].plot(ts[mask],(trace['slider'][mask]+.03267458688196273)*1000,label=label,color=color);axes[1].plot(ts[mask],np.linalg.norm(rv[mask],axis=1),color=color)
  time=[];moment=[];joint=[]
  for line in (path/'wrap-contact-physical-steps.jsonl').open():
   r=json.loads(line)
   if r['time_s']<14:continue
   cs=[c for c in r['contacts'] if c['knife_link']=='link_0'];time.append(r['time_s']);moment.append(np.sum([c['normal_moment_about_body_origin_Nm'] for c in cs],axis=0) if cs else np.zeros(3));joint.append(sum(c['normal_magnitude_N'] for c in cs if c['hand_link']=='hand_r_middle_link4'))
  time=np.asarray(time);moment=np.asarray(moment);joint=np.asarray(joint);hz=round(1/np.median(np.diff(time)));block=max(1,round(hz/10));n=len(time)//block;tb=time[:n*block].reshape(n,block).mean(1);mb=moment[:n*block].reshape(n,block,3).mean(1);jb=joint[:n*block].reshape(n,block).mean(1)
  axes[2].plot(tb,mb[:,2]*1000,color=color);axes[3].plot(tb,jb,color=color)
  ev=json.loads((path/'functional-evaluation.json').read_text());rows.append(dict(label=label,trial=str(path),evaluation=ev,normal_moment_mean_Nm=moment.mean(0).tolist(),middle_link4_mean_normal_N=float(joint.mean()),trace_sha256=hashlib.sha256((path/'trace.npz').read_bytes()).hexdigest(),contacts_sha256=hashlib.sha256((path/'wrap-contact-physical-steps.jsonl').read_bytes()).hexdigest()))
 labels=['Slider endpoint position mm','Relative rotation from16s rad','Body-contact normal moment\nabout knife long axis mN m','Actual middle joint4\nbody-normal reaction N']
 for ax,label in zip(axes,labels):
  ax.set_ylabel(label);ax.grid(alpha=.25)
  for t in [16,21,26,31]:ax.axvline(t,color='k',lw=.6,alpha=.3)
 axes[0].legend(ncol=3);axes[-1].set_xlabel('Physical simulation time s');fig.suptitle('Matched nominal original-knife trials: support migration, normal moments and cross-cycle drift\nNormal moment excludes friction/rail and is NOT net torque, axial push/pull force, contact area or causal proof.',fontsize=12);fig.tight_layout(rect=[0,0,1,.95])
 for suffix in ['png','pdf','svg']:fig.savefig(a.output/('support-moments.'+suffix),dpi=160)
 (a.output/'results.json').write_text(json.dumps(dict(scope=__doc__,cases=rows,averaging='100ms plot bins from original240Hz body-contact normals; actual trace remains30Hz',causality_claim=False),indent=2));print(a.output)
if __name__=='__main__':main()
