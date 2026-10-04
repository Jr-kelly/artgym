"""Compare actual normal-force/rail/slip records; no new physics or force estimate."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    cases=[('V17 nominal /750 functional','actual-table-projected-grasp-frozen750-load2-v17'),('V18 highercapacity /750 failed','actual-table-projected-grasp-frozen750-load5-v18'),('V33 thin /new50 failed','actual-table-thin-table-prior-range04-frozen50-load2-v33'),('V37 ringtracking /750 failed','actual-table-ring-tracking-acquisition-frozen750-load5-v37')]
    fig,axes=plt.subplots(4,4,figsize=(16,12),sharex=True);receipt=[]
    for row,(label,name) in enumerate(cases):
        d=R/'runs/antirotation-grasp-20261004/continuous'/name;t=np.load(d/'trace.npz');e=np.load(d/'relative-hand-evaluation.npz');r=json.loads((d/'report.json').read_text());lower=float(ET.parse(R/r['physical_asset']).find('.//joint[@type="prismatic"]/limit').get('lower'));clock=t['time'];m=clock>=16
        axes[row,0].plot(clock[m],(t['slider'][m]-lower)*1000,color='#2364aa',label='Actual rail position');axes[row,0].axhline(25,color='gray',ls=':',lw=.8);axes[row,0].axhline(8,color='gray',ls=':',lw=.8)
        axes[row,1].plot(clock[m],t['pair_slider_pressure_mean_N'][m,0],color='#2364aa',label='Thumb-slider NORMAL');axes[row,1].plot(clock[m],t['solver_brake_capacity_N'][m],color='#ca6d1b',label='Native capacity parameter');axes[row,1].set_ylim(bottom=0)
        axes[row,2].plot(clock[m],t['pair_slider_axial_normal_contribution_mean_N'][m,0],color='#8b458a',label='Thumb-slider axial NORMAL');axes[row,2].axhline(0,color='gray',lw=.7)
        axes[row,3].plot(clock[m],np.linalg.norm(e['relative_rotvec_rad'][m],axis=1),color='#2364aa',label='Knife rotation relative to wrist');axes[row,3].plot(clock[m],e['active_wrist_rotation_rad'][m],color='#ca6d1b',label='Active wrist rotation')
        phase_stats=[]
        for phase,start,end in [('extend1',16,21),('return1',21,26),('extend2',26,31),('return2',31,36)]:
            q=(clock>start)&(clock<=end+.001)
            phase_stats.append({'phase':phase,'thumb_slider_normal_mean_N':float(t['pair_slider_pressure_mean_N'][q,0].mean()),'thumb_slider_axial_normal_mean_N':float(t['pair_slider_axial_normal_contribution_mean_N'][q,0].mean()),'thumb_slider_contact_fraction':float(t['pair_slider_contact_substep_fraction'][q,0].mean()),'index_body_contact_fraction':float(t['pair_body_contact_substep_fraction'][q,1].mean()),'ring_body_contact_fraction':float(t['pair_body_contact_substep_fraction'][q,3].mean())})
        for col,ax in enumerate(axes[row]):
            ax.set_xlim(16,36);ax.grid(alpha=.18)
            for start,end in [(21,26),(31,36)]:ax.axvspan(start,end,color='gray',alpha=.10)
            if col==0:ax.set_ylabel(label+'\nposition (mm)',fontsize=9)
        receipt.append({'trial':name,'role':'Frozen development only; controllers/geometry differ, not matched solevariable comparison','trace_sha256':hashlib.sha256((d/'trace.npz').read_bytes()).hexdigest(),'phases':phase_stats})
    for ax,title in zip(axes[0],['Measured rail position','NORMAL pressure and native capacity (N)','Axial NORMAL contribution only (N)','Relative/active rotation (rad)']):ax.set_title(title,fontsize=10)
    for ax in axes[-1]:ax.set_xlabel('Actual continuous simulation time (s)')
    for ax in axes[0]:ax.legend(fontsize=7,loc='upper left')
    fig.suptitle('Loaded return: normal pressure is not axial traction or constant force\nGray: return/hold. Capacity is a physics parameter; actual brake force and frictional traction unavailable.',fontsize=13);fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(a.output/'loaded-return-evidence.png',dpi=160);fig.savefig(a.output/'loaded-return-evidence.pdf');plt.close(fig)
    (a.output/'loaded-return-evidence.json').write_text(json.dumps({'scope':'Offline existing actualtraces only. Calibrated forceon slider, positive localz. Normal projection excludesfriction and must not be used as total tangential force, actuator estimate, constantpressure or real-world ceiling. Fourdevelopment cases differ inmechanics/control; no causal or successrate claim.','cases':receipt},indent=2)+'\n');print(str(a.output))
if __name__=='__main__':main()
