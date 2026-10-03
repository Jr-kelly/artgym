"""Standalone development observer figure; no new physical experiments."""
import pathlib,json,hashlib
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.record_wuji_support_goal import record
R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003';D=R/'research/support-pressure-20261003';out=B/'figures/support-observer-v152';out.mkdir(parents=True,exist_ok=False)
record('support_observer_v152_figure_started',evidence=str(out.relative_to(R)),next='Plotpredeclaredfirstenvs ofvalidationphysicalgroups0/5, notoutcome-selected; allgroup errors separate frompolicybehavior.')
fresh=np.load(B/'observer-head-v149/fresh-predictions.npz');fit=np.load(B/'observer-data-fit-v148/data.npz');p=fresh['predictions'].copy();p[:,0]=p[:,0].clip(-.25,1.5);p[:,1:7]=p[:,1:7].clip(-4,4);y=fresh['labels'];groups=fresh['groups'];t=fresh['times'];constant=fit['labels'][fit['groups']%5!=0].mean(0);valid=groups%5==0
error=np.linalg.norm((p[:,4:7]-y[:,4:7])*.25,axis=1);base=np.linalg.norm((constant[None,4:7]-y[:,4:7])*.25,axis=1);near=(np.linalg.norm(y[:,1:4],axis=1)<1)&(y[:,7]>.5)&valid
summary=dict(fresh_disjoint_physical_groups=13,fresh_validation_rows=int(valid.sum()),rotation_vector_norm_mae_rad=float(error[valid].mean()),constant_rotation_vector_norm_mae_rad=float(base[valid].mean()),rotation_vector_norm_p90_rad=float(np.quantile(error[valid],.9)),retained_translation_contact_proxy_rows=int(near.sum()),retained_rotation_vector_norm_mae_rad=float(error[near].mean()),retained_constant_rotation_vector_norm_mae_rad=float(base[near].mean()),scope='Bounded pose labels relative noisyinitial estimate, not actual16s evaluationreference. Retained subset is descriptive only, allfailedchains includedinfit andallgroupmetrics. Neither force/pose sensor nor behavior improvement.')
fig,axes=plt.subplots(3,2,figsize=(11,8),sharex=True,layout='constrained')
for col,group in enumerate([0,5]):
 first=int(np.flatnonzero(groups[:512]==group)[0]);ids=np.arange(first,len(y),512);assert np.all(groups[ids]==group)
 values=[(np.linalg.norm(y[ids,4:7],axis=1)*.25,np.linalg.norm(p[ids,4:7],axis=1)*.25,float(np.linalg.norm(constant[4:7])*.25),'Bounded angle from initial estimate (rad)'),(y[ids,0]*40,p[ids,0]*40,float(constant[0]*40),'Slider progress label (mm)'),(y[ids,7],p[ids,7],float(constant[7]),'Contact proximity proxy')]
 for row,(truth,predicted,basevalue,label) in enumerate(values):
  ax=axes[row,col];ax.plot(t[ids],truth,color='#222222',lw=1.8,label='Simulator label');ax.plot(t[ids],predicted,color='#0072b2',lw=1.6,label='Legal-history estimate');ax.axhline(basevalue,color='#d55e00',ls='--',lw=1.1,label='Training-mean baseline');ax.set_ylabel(label);ax.grid(alpha=.18)
 axes[0,col].set_title(f'Validation physical group {group}, first environment {first}')
 axes[2,col].set_xlabel('Known task time (s)');axes[2,col].set_ylim(-.05,1.05)
axes[0,0].legend(fontsize=8);fig.suptitle('Pose observability remains limited despite progress/contact-proxy fitting',fontsize=14)
for ext in ['png','svg','pdf']:fig.savefig(out/('support-observer.'+ext),dpi=180)
plt.close(fig)
provenance=dict(summary=summary,head_sha256='f5f6e6926f0564eae122e7cd9b0842d6ed9b476e5be646e57ff53e34287fa99b',dataset_hashes={'fit':'27c1e00d943ed5ff546e2c99bce8fe870940e764889f2ae0439908dbdd8625b0','fresh':'82f353a7c286df3b6ebf6f1bc1bee441f50b724445b6bd59d95a23831479b1d3'},selection='First environments ofpredeclared validationgroups0/5; no outcome filtering',role='Supervised observerdevelopment only; frozen4independentpolicychecks excluded, controllerbehavior separatelytested')
(out/'provenance.json').write_text(json.dumps(provenance,indent=2));(D/'observer-observability-v152-summary.json').write_text(json.dumps(provenance,indent=2));record('support_observer_v152_figure_closed',evidence=str(out.relative_to(R)/'provenance.json'),config=summary,next='Actualmatched50update controlpilot, not extrapolatefitting tofull demo ormethodadvantage.');print(json.dumps(summary))
