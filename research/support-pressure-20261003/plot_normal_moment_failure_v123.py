"""Standalone research figure of failed modelmoment control; no online inputs."""
import json,hashlib,pathlib,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
from scripts.record_wuji_support_goal import record,R,D
B=R/'runs/support-pressure-20261003';out=B/'figures/normal-moment-v123';out.mkdir(parents=True,exist_ok=False);fig,axes=plt.subplots(3,2,figsize=(11,8),sharex=True);rows=[]
record('normal_moment_failure_v123_figure_started',conclusion='Use alreadycompletedtwo v111 traces, no additionalphysics/training. Comparelegalmodel moment against normal-only solver moment in labelleddifferentframes; fullfrictionwrench unavailable.',next='Standalonepublication-sizedplot and provenance, not another feedbackcandidate')
for column,label in enumerate(['nominal','raised1']):
 p=B/'demo'/(label+'-moment-support-moment-retention-v111');z=np.load(p/'trace.npz');r=json.loads((p/'report.json').read_text());t=z['time'];m=(t>=14.3)&(t<16);proxy=z['estimated_contact_normal_moment_proxy_Nm'];normal=z['pair_all_contact_normal_moment_knife_mean_Nm'].sum(1)[:,2]
 axes[0,column].plot(t,z['pair_slider_pressure_mean_N'][:,0],label='Solver thumb-slider normal');axes[0,column].set_title(label+' | continuous demo FAIL');axes[0,column].set_ylabel('Normal force (N)');axes[0,column].set_ylim(0,1.65)
 axes[1,column].plot(t,normal*1000,label='Solver normals | current knife frame');axes[1,column].plot(t-1/30,proxy*1000,label='Legal model | initial estimated frame');axes[1,column].set_ylabel('Z normal moment (mNm)')
 i=np.flatnonzero(t>=16)[0];rotation=(Rotation.from_quat(z['object'][i,3:7]).inv()*Rotation.from_quat(z['object'][:,3:7])).magnitude();axes[2,column].plot(t,rotation,label='Actual body rotation | evaluation only');axes[2,column].axhline(.25,color='r',linestyle='--',label='Original 0.25 rad bound');axes[2,column].set_ylabel('Body rotation (rad)');axes[2,column].set_xlabel('Episode time (s)')
 for ax in axes[:,column]:
  for start in [16,21,26,31]:ax.axvline(start,color='.7',linewidth=.7)
  ax.set_xlim(14.3,36);ax.grid(alpha=.2);ax.legend(fontsize=7,loc='best')
 rows.append(dict(label=label,trace=str((p/'trace.npz').relative_to(R)),trace_sha256=hashlib.sha256((p/'trace.npz').read_bytes()).hexdigest(),weight_sha256=list(r['weight_sha256'].values())[-1],static_model_moment_mNm=float(proxy[m].mean()*1000),static_solver_normal_moment_mNm=float(normal[m].mean()*1000),full_success=r['full_success'],body_rotation_rad=r['operation_body_max_rotation_rad']))
fig.suptitle('Failed support-moment retention: scalar load accuracy does not establish a contact wrench',fontsize=12);fig.tight_layout(rect=(0,.035,1,.96));fig.text(.02,.015,'Normal contribution only: friction traction/moment is unavailable. Model geometry is an initial noisy estimate, not measured contact or pose.',fontsize=8)
for suffix in ['png','pdf','svg']:fig.savefig(out/('normal-moment-failure.'+suffix),dpi=180)
plt.close(fig);provenance=dict(cases=rows,scope='Two developmentfailures, not independentvalidation. Frames/geometricorigins differ transparently. No fullmoment reconstruction, real sensorclaim or causalproof. No newphysicsruns.',time_alignment='Native trace saved atcontrolframeend; legalcontrollerproxy computed atframebegin(time-1/30); actualsolvernormalmoment is8physicalsubstepaverage.')
(out/'provenance.json').write_text(json.dumps(provenance,indent=2));record('normal_moment_failure_v123_figure_closed',evidence=str(out.relative_to(R)/'provenance.json'),conclusion='Initialgeometry single-normalproxy misses severalmNm ofnormal-contact moment. Neither quantity isfullfrictionwrench; do nottune failedcontroller from scalarproxyconfidence alone.',next='Waitforactualpilot conclusions; finalreport keeps estimate/solver/hardware distinction');print(json.dumps(provenance))
