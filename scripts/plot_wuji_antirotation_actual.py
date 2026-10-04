"""Scientific curves from archived actual continuous simulation, no new trials."""
import argparse,json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 root=R/'runs/antirotation-grasp-20261004/continuous';cases=[('actual-table-projected-grasp-frozen750-load2-v17','V17 nominal .2/.2 frozen750'),('actual-table-projected-grasp-frozen750-load5-v18','V18 nominal .5/.5 frozen750'),('actual-table-projected-retain750-frozen50-load5-v21','V21 nominal .5/.5 trained50 negative'),('actual-table-thin-allcontact-frozen750-load2-v24','V24 thin .2/.2 frozen750')];fig,axes=plt.subplots(3,2,figsize=(14,11),sharex=True);evidence=[]
 for name,label in cases:
  folder=root/name;t=np.load(folder/'trace.npz');rel=np.load(folder/'relative-hand-evaluation.npz');report=json.loads((folder/'report.json').read_text());asset=R/report['physical_asset'];lower=float(ET.parse(asset).find('.//joint[@type="prismatic"]/limit').get('lower'));time=t['time'];mask=time>=16;pressure=t['pair_slider_pressure_mean_N'][:,0];values=[(t['slider']-lower)*1000,np.rad2deg(np.linalg.norm(rel['relative_rotvec_rad'],axis=1)),np.linalg.norm(rel['relative_translation_m'],axis=1)*1000,pressure,t['pair_slider_contact_substep_fraction'][:,0],np.linalg.norm(t['pair_force_normal_contribution_world_mean_N'][:,1,0,:],axis=1)]
  for index,(ax,y) in enumerate(zip(axes.flat,values)):
   if index in [1,2]:y=np.where(mask,y,np.nan)
   ax.plot(time,y,label=label,lw=1.3)
  evidence.append(dict(trial=name,trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest(),functional=json.loads((folder/'functional-evaluation.json').read_text()),operation_thumb_normal_mean_N=float(pressure[mask].mean()),operation_thumb_normal_p05_N=float(np.quantile(pressure[mask],.05)),operation_thumb_normal_max_N=float(pressure[mask].max())))
 labels=['Authored rail displacement (mm)','Knife rotation relative to hand at16s (deg)','Knife translation relative to hand at16s (mm)','Measured thumb-slider normal pressure (N)','Exact thumb-slider contact substep fraction','Index-handle normal contribution resultant (N)']
 for ax,label in zip(axes.flat,labels):
  ax.set_ylabel(label,fontsize=9);ax.grid(alpha=.2);ax.set_xlim(0,36);ax.axvspan(0,16,color='gray',alpha=.07)
  for t in [16,21,26,31,36]:ax.axvline(t,color='gray',lw=.6,alpha=.5)
 axes[0,0].step([0,16,21,26,31,36],[0,40,0,40,0,0],where='post',color='black',ls='--',lw=.8,label='External command,40mm unchanged');axes[0,0].set_ylim(-1,43);axes[2,0].set_ylim(-.02,1.05)
 for ax in axes[-1]:ax.set_xlabel('Physical continuous time (s)')
 handles,leg=axes[0,0].get_legend_handles_labels();fig.legend(handles,leg,loc='lower center',ncol=2,fontsize=9);fig.suptitle('Actual tabletop pickup + two loaded cycles: development evidence\n0–16s pickup/settling;16–21/26–31 extend,21–26/31–36 retract. Normal force excludes frictional traction.',fontsize=12);fig.tight_layout(rect=[0,.085,1,.95]);fig.savefig(a.output/'actual-development-comparison.png',dpi=160);fig.savefig(a.output/'actual-development-comparison.pdf');plt.close(fig);(a.output/'actual-development-comparison.json').write_text(json.dumps(dict(scope='Offline scientific evidence from existing development simulation only; no independent success rate, hardware force measurement or reconstructed frictional wrench.',cases=evidence),indent=2));print(str(a.output))
if __name__=='__main__':main()
