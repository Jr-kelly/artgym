"""Export paired actual-physics capacity traces; evaluation-only quantities."""
import argparse, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--successful',type=Path,required=True)
    parser.add_argument('--failure',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,layout='constrained')
    traces=[];manifest={'scope':'Paired developmental actual TABLE chains. Evaluation-only simulated normal solver contacts; not hardware force, tangential force or constant-pressure regulation. Same P50/reference, sensor seed and materials; added running/startup terms differ.', 'sources':[]}
    for folder,color in [(args.successful,'#246bce'),(args.failure,'#b83737')]:
        report=json.loads((folder/'report.json').read_text());trace=np.load(folder/'trace.npz')
        lower=float(ET.parse(report['physical_asset']).find('./joint/limit').get('lower'))
        time=trace['time'];operation=trace['phase']>=4;reference_index=np.flatnonzero(time<16)[-1]
        rotation=(Rotation.from_quat(trace['object'][reference_index,3:7]).inv()*Rotation.from_quat(trace['object'][:,3:7])).magnitude()
        label=f"Added run/startup amplitudes {report['added_load_N']:.2f}/{report['passive_startup_detent_amplitude_N']:.2f} N"
        axes[0,0].plot(time[operation],1000*(trace['slider'][operation]-lower),color=color,label=label)
        axes[0,1].plot(time[operation],trace['finger_slider_solver_magnitude'][operation,0],color=color,label=label)
        axes[1,0].plot(time[operation],np.rad2deg(rotation[operation]),color=color)
        axes[1,1].plot(time[operation],trace['load'][operation],color=color)
        manifest['sources'].append({'trial':str(folder),'report_sha256':hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),'trace_sha256':hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest(),'contact_schema':json.loads((folder/'contact-schema.json').read_text()),'full_success':report['full_success']})
        traces.append(time)
    time=traces[0];operation=time>16+1e-6
    # Samples are stamped after a control interval; command was issued before it.
    phase=np.clip(np.floor((time[operation]-16-1/60)/5),0,3).astype(int)
    goal=np.where(phase%2==0,40,0)
    axes[0,0].step(time[operation],goal,where='post',color='#555555',linestyle='--',label='Known scheduled command')
    axes[1,0].axhline(np.rad2deg(.25),color='#555555',linestyle='--',label='Predeclared stability diagnostic')
    labels=['Actual slider travel [mm]','Thumb-slider normal solver magnitude [N]','Knife rotation from handover [degrees]','Actual added joint load [N]']
    for ax,label in zip(axes.flat,labels):
        ax.set_ylabel(label);ax.set_xlim(16,36);ax.grid(alpha=.2)
        for edge in [21,26,31]:ax.axvline(edge,color='#aaaaaa',linewidth=.5)
    for ax in axes[1]:ax.set_xlabel('Continuous episode time [s]')
    axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8)
    fig.suptitle('Same learned hybrid controller: maintained contact vs support/contact breakdown')
    fig.savefig(args.output/'paired-capacity.png',dpi=180)
    fig.savefig(args.output/'paired-capacity.pdf')
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2));plt.close(fig)


if __name__=='__main__':main()
