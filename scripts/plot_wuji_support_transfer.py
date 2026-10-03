"""Paired development figure: same policy/input/load, different support path."""
import json,pathlib,hashlib,csv
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=pathlib.Path(__file__).resolve().parents[1];B=R/'runs/support-pressure-20261003'
out=B/'figures/support-transfer-v92';out.mkdir(parents=True,exist_ok=False)
fig,axes=plt.subplots(4,2,figsize=(12,12),sharex=True);receipts=[]
for column,condition in enumerate(['nominal','raised1']):
    for kind,suffix,color,style in [('direct','coordinated-brace-v82','#929292','--'),('sequential','staged-transfer-v87','#1769a4','-')]:
        folder=B/'demo'/(condition+'-'+suffix);z=np.load(folder/'trace.npz');report=json.loads((folder/'report.json').read_text())
        t=z['time'];mask=t>=12;op=t>=16;reference=np.argmin(abs(t-16))
        rotation=(Rotation.from_quat(z['object'][reference,3:7]).inv()*Rotation.from_quat(z['object'][:,3:7])).magnitude()
        axes[0,column].plot(t[mask],z['pair_slider_pressure_mean_N'][mask,0],color=color,ls=style,label=kind,lw=1.5)
        axes[1,column].plot(t[op],rotation[op],color=color,ls=style,lw=1.5)
        axes[2,column].plot(t[mask],(z['slider'][mask]-z['slider'][0])*1000,color=color,ls=style,lw=1.5)
        actual=Rotation.from_quat(z['object'][:,3:7]).inv()
        points=z['pair_underside_contact_position_world_mean_m']
        local=np.stack([actual.apply(points[:,j]-z['object'][:,:3]) for j in range(5)],1)
        for j,finger,fcolor in [(1,'index','#d95f02'),(2,'middle','#1b9e77'),(4,'pinky','#7570b3')]:
            x=local[:,j,0]*1000;x[z['pair_underside_support_mean_N'][:,j]<=.01]=np.nan
            axes[3,column].plot(t[mask],x[mask],color=fcolor,ls=style,alpha=.9 if kind=='sequential' else .35,lw=1,label=finger if kind=='sequential' else None)
        receipts.append(dict(condition=condition,path=kind,report=report,trace_sha256=hashlib.sha256((folder/'trace.npz').read_bytes()).hexdigest()))
    axes[0,column].set_title('Nominal: noisy initial estimate' if column==0 else 'Slider protrusion +1 mm: noisy initial estimate')
    axes[1,column].axhline(.25,color='#b3261e',ls=':',lw=1,label='original body limit')
    axes[2,column].axhline(25,color='#b3261e',ls=':',lw=1)
    for edge in [-8,0,8]:axes[3,column].axhline(edge,color='black',ls=':',lw=.6,alpha=.5)
    for row in range(4):
        axes[row,column].axvspan(12,16,color='#eef1f4',zorder=-1)
        axes[row,column].axvline(16,color='black',lw=.6)
        axes[row,column].grid(alpha=.2);axes[row,column].set_xlim(12,36)
    axes[0,column].legend(loc='upper right');axes[3,column].legend(loc='upper right',ncol=3)
axes[0,0].set_ylabel('Thumb-slider normal force (N)')
axes[1,0].set_ylabel('Body rotation from handover (rad)')
axes[2,0].set_ylabel('Actual rail travel (mm)')
axes[3,0].set_ylabel('Mean underside contact x (mm)')
for ax in axes[-1]:ax.set_xlabel('Continuous episode time (s)')
fig.suptitle('Motor-only support transfer: direct joint ramp vs withdraw / cross / recontact\nSame750 policy, original pickup, 0.5/0.5 N model amplitudes; development pairs, one attempt each',fontsize=12)
fig.text(.08,.012,'Forces: native normal pairs, 240 Hz with 8-step mean. Contact points: unweighted positive-normal contact means; not a full frictional wrench.\nShaded12--16s is preparation; original body criterion applies during16--36s. All outcomes, including failures, retained.',fontsize=8)
fig.tight_layout(rect=[0,.045,1,.94])
for extension in ['png','svg','pdf']:fig.savefig(out/('support-transfer.'+extension),dpi=170)
(out/'provenance.json').write_text(json.dumps(dict(scope='Paired actualcontinuous development evidence only; not independentvalidation or causal proof of completecontactwrench.',cases=receipts),indent=2))
print(json.dumps(dict(output=str(out),cases=4)))
