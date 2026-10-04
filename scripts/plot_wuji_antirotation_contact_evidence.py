"""Publication artifact for measured normal-contact signatures in development.

Normal-force contributions omit tangential friction. They are diagnostic truth,
never policy inputs, force-control targets, or proof of a single failure cause.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path('runs/antirotation-grasp-20261004')
CASES=[('V17 nominal .2/.2','actual-table-projected-grasp-frozen750-load2-v17'),('V18 nominal .5/.5','actual-table-projected-grasp-frozen750-load5-v18'),('V24 thin .2/.2','actual-table-thin-allcontact-frozen750-load2-v24'),('V26 thin index retention','actual-table-thin-index-retention-frozen750-load2-v26')]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(4,4,figsize=(16,11),sharex=True);summary=[]
    for row,(label,name) in enumerate(CASES):
        folder=B/'continuous'/name;t=np.load(folder/'trace.npz');evaluation=json.loads((folder/'functional-evaluation.json').read_text());relative=np.load(folder/'relative-hand-evaluation.npz');clock=t['time'];mask=clock>=16
        # Authored knife long axis is local Z. The saved force/moment arrays
        # use declared finger order thumb,index,middle,ring,pinky.
        index=np.linalg.norm(t['pair_force_normal_contribution_world_mean_N'][:,1,0,:],axis=-1)
        support_moment=t['pair_all_contact_normal_moment_knife_mean_Nm'][:,[1,2,4],2].sum(axis=1)*1000
        axes[row,0].plot(clock,t['pair_slider_pressure_mean_N'][:,0],label='Thumb / slider');axes[row,0].plot(clock,index,label='Index / handle');axes[row,0].set_ylabel(label+'\nNormal N')
        axes[row,1].plot(clock,support_moment,label='Support long-axis moment');axes[row,1].set_ylabel('Normal contribution mN m')
        lower=-.03267458688196273;axes[row,2].plot(clock,(t['slider']-lower)*1000,label='Actual rail travel');axes[row,2].set_ylabel('Travel mm')
        axes[row,3].plot(relative['time'],np.linalg.norm(relative['relative_rotvec_rad'],axis=-1),label='Knife relative to wrist');axes[row,3].set_ylabel('Relative rotation rad')
        for ax in axes[row]:
            ax.set_xlim(14,36);ax.grid(alpha=.2)
            for at in [16,21,26,31]:ax.axvline(at,color='.6',lw=.7,ls=':')
        metrics=[]
        for start,end in [(14,16),(16,21),(21,26),(26,31),(31,36)]:
            m=(clock>=start)&(clock<end)
            metrics.append(dict(interval_s=[start,end],thumb_slider_normal_mean_N=float(t['pair_slider_pressure_mean_N'][m,0].mean()),index_handle_normal_resultant_mean_N=float(index[m].mean()),support_long_axis_normal_moment_mean_mNm=float(support_moment[m].mean()),thumb_contact_substep_fraction=float(t['pair_slider_contact_substep_fraction'][m,0].mean())))
        summary.append(dict(case=label,trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest(),functional_pass=evaluation['continuous_pickup_demo_pass'],endpoints_m=evaluation['slider_endpoints_m'],intervals=metrics))
    for ax in axes[-1]:ax.set_xlabel('Continuous simulation time s')
    for ax in axes[0]:ax.legend(fontsize=8)
    fig.suptitle('Actual pickup and two cycles: normal-contact signatures (development cases)\nNormal contributions exclude frictional traction; no live-force policy input or causal identification',fontsize=12)
    fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(a.output/'contact-signatures.png',dpi=170);fig.savefig(a.output/'contact-signatures.pdf');plt.close(fig)
    report=dict(scope='Four distinct retained development mechanics/results; no new physicalrollout, normalforce signatures only, no traction reconstruction/force control/causalproof or independent generalization claim',finger_order=['thumb','index','middle','ring','pinky'],normal_force_field_units='N, calibrated contact lambda without extra dt division; arithmetic physical-substep means',rows=summary)
    (a.output/'contact-signatures.json').write_text(json.dumps(report,indent=2));print(json.dumps({'output':str(a.output),'cases':len(summary),'scope':report['scope']}))
if __name__=='__main__':main()
