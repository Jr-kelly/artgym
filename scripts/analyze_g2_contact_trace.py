"""Reproducible failure-phase diagnostics for continuous G2 physics traces."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import FINGERS
def main():
    p=argparse.ArgumentParser();p.add_argument('--demo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plot',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    z=np.load(a.demo/'trace.npz');plan=json.loads((a.demo/'plan.json').read_text());report=json.loads((a.demo/'report.json').read_text());t=z['time'];lower=-.03267458688196273;distance=z['slider']-lower;reference=int(np.argmin(abs(t-16)));bodyq=Rotation.from_quat(z['object'][:,3:7]);angle=(Rotation.from_quat(z['object'][reference,3:7]).inv()*bodyq).magnitude();drift=np.linalg.norm(z['object'][:,:3]-z['object'][reference,:3],axis=1)
    pair_data=all(k in z.files for k in ['finger_slider_contacts','finger_body_contacts','finger_slider_solver_magnitude','finger_body_solver_magnitude'])
    stages=[(0,5,'settle/approach'),(5,8,'close'),(8,12,'lift'),(12,16,'hold/real history'),(16,21,'extend1'),(21,26,'retract1'),(26,31,'extend2'),(31,36,'retract2')];rows=[]
    for lo,hi,name in stages:
        sel=(t>lo)&(t<=hi)
        if not sel.any():continue
        rows.append(dict(stage=name,time_s=[lo,hi],frames=int(sel.sum()),height_min_m=float(z['object'][sel,2].min()),thumb_slider_contact_fraction=float((z['finger_slider_contacts'][sel,0]>0).mean()) if pair_data else None,finger_body_contact_fractions=(z['finger_body_contacts'][sel]>0).mean(0).tolist() if pair_data else None,mean_thumb_slider_solver_magnitude=float(z['finger_slider_solver_magnitude'][sel,0].mean()) if pair_data else None,mean_finger_body_solver_magnitudes=z['finger_body_solver_magnitude'][sel].mean(0).tolist() if pair_data else None,slider_from_lower_range_m=[float(distance[sel].min()),float(distance[sel].max())],body_rotation_from_handover_max_rad=float(angle[sel].max()),body_drift_from_handover_max_m=float(drift[sel].max())))
    result=dict(demo=str(a.demo),configuration=plan['args'],weight_sha256=report['weight_sha256'],reported_full_success=report['full_success'],reported_first_failure=report['first_failure'],fingers=list(FINGERS),exact_pair_contacts_recorded=pair_data,rows=rows,scope='Recorded continuous simulation, exact contact-pair presence; simulated solver normal magnitude is neither hardware force nor constant-force regulation; static height on table is not pickup')
    (a.output/'phases.json').write_text(json.dumps(result,indent=2))
    if a.plot:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(4,1,figsize=(12,10),sharex=True,layout='constrained')
        axes[0].plot(t,distance*1000,label='actual passive slider');goal=np.where(((t-16)//5).astype(int)%2==0,40,0);goal[t<16]=0
        if not report['operation_evaluated']:goal[:]=0
        axes[0].plot(t,goal,'k--',label='scheduled goal' if report['operation_evaluated'] else 'operation not executed');axes[0].set_ylabel('Slider (mm)');axes[0].legend(loc='upper left')
        axes[1].plot(t,z['object'][:,2],label='body height');axes[1].axhline(plan['args']['table_height'],color='k',ls=':',label='table top');axes[1].set_ylabel('Height (m)');axes[1].legend(loc='upper left');right=axes[1].twinx();right.plot(t,angle,color='tab:red',alpha=.7);right.set_ylabel('Rotation from 16s (rad)',color='tab:red')
        if pair_data:
            contacts=np.r_[(z['finger_slider_contacts'][:,0]>0)[None],(z['finger_body_contacts']>0).T];axes[2].imshow(contacts,origin='upper',aspect='auto',extent=[t[0],t[-1],5.5,-.5],vmin=0,vmax=1,cmap='Greys');axes[2].set_yticks(range(6),['thumb-slider']+[f+'-body' for f in FINGERS]);axes[2].set_ylabel('Pair presence')
            axes[3].plot(t,z['finger_slider_solver_magnitude'][:,0],label='thumb-slider normal solver magnitude');axes[3].plot(t,z['finger_body_solver_magnitude'][:,1:].sum(1),label='support-body sum');axes[3].set_ylabel('Simulated solver magnitude');axes[3].set_xlabel('Continuous episode time (s)');axes[3].legend(loc='upper left')
        else:
            for ax in axes[2:]:ax.text(.5,.5,'Exact pair contacts were not recorded in this older trace',ha='center',transform=ax.transAxes)
        for ax in axes:
            for boundary in [5,8,12,16,21,26,31]:ax.axvline(boundary,color='grey',ls=':',alpha=.4)
            ax.grid(alpha=.15)
        fig.suptitle(a.demo.name+' | continuous simulation | full_success='+str(report['full_success']));fig.savefig(a.output/'contact-phases.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(output=str(a.output),full_success=report['full_success'],first_failure=report['first_failure'])))
if __name__=='__main__':main()
