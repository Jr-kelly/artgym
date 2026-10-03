"""Measured joint lag and evaluated physical pressure are different quantities."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 root=Path(__file__).resolve().parents[1];fig,axes=plt.subplots(3,2,figsize=(12,9),sharex=True,layout='constrained');manifest=[]
 for name,label,color in [('g2-proprio-middle-v5-full-v60','v60 fixed support + prior thumb curve','#3569af'),('g2-coupled-lag-regulated-full-v61','v61 lag regulator + coupled curve','#be4939'),('g2-coupled-static-middle-full-v62','v62 fixed support + coupled curve','#49825a')]:
  folder=root/'runs/robust-knife-family-20261003/demo'/name;r=json.loads((folder/'report.json').read_text());meta=json.loads((folder/'physics.json').read_text());tr=np.load(folder/'trace.npz');t=tr['time'];m=t>=16;index=meta['hand_indices'][7];target=tr['target'][:,index];lag=tr['observed_q'][:,7]-target;reference=np.flatnonzero(t<16)[-1];rotation=(Rotation.from_quat(tr['object'][reference,3:7]).inv()*Rotation.from_quat(tr['object'][:,3:7])).magnitude();lower=float(ET.parse(root/r['physical_asset']).find('./joint/limit').get('lower'))
  values=[target,lag,tr['finger_body_solver_magnitude'][:,2],tr['finger_slider_solver_magnitude'][:,0],rotation,1000*(tr['slider']-lower)]
  for ax,val in zip(axes.flat,values):ax.plot(t[m],val[m],label=label,color=color,linewidth=1)
  manifest.append(dict(trial=str(folder.relative_to(root)),report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest(),maximum_rotation_rad=r['operation_body_max_rotation_rad'],scope='Script developmental TABLE, all fail original body-stability criterion; v61-v62 same coupled reference'))
 labels=['Middle joint4 target [rad]','Observed minus issued joint [rad]','Middle-body solver normal [N, simulation]','Thumb-slider solver normal [N, simulation]','Knife rotation from handover [rad]','Slider travel [mm]']
 for ax,label in zip(axes.flat,labels):
  ax.set_ylabel(label);ax.set_xlim(16,36);ax.grid(alpha=.2)
  for edge in [21,26,31]:ax.axvline(edge,color='#aaa',linewidth=.5)
 axes[2,0].axhline(.25,color='#555',linestyle='--',label='Original stability diagnostic')
 axes[0,0].legend(fontsize=7);axes[2,0].legend(fontsize=7)
 for ax in axes[-1]:ax.set_xlabel('Continuous episode time [s]')
 fig.suptitle('Support and thumb coordination: joint-load proxy does not establish constant pressure')
 fig.savefig(a.output/'middle-feedback.png',dpi=170);fig.savefig(a.output/'middle-feedback.pdf');plt.close(fig)
 (a.output/'manifest.json').write_text(json.dumps(dict(sources=manifest,scope='Actual solver-contact evaluation, not physical sensor/force calibration. v60-v61 changes both reference and feedback; only v61-v62 is the matched operation-feedback contrast. Endpoints alone do not make a complete demo.'),indent=2))


if __name__=='__main__':main()
