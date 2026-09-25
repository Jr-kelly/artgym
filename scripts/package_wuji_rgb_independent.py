"""Package all frozen independent-cohort results after the complete final audit."""
from pathlib import Path
import hashlib,json,shutil,zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.package_wuji_dagger_final import split_archive

def main():
 r=Path(__file__).resolve().parents[1];g=r/'runs/wuji-goal';d=g/'diagnostics';run=d/'rgb-independent-paired-1729-v1';final=d/'rgb-finalization-1802-v1'
 f=json.loads((final/'status.json').read_text());assert f['status']=='completed' and all(x['returncode']==0 for x in f['stages'])
 a_path=d/'rgb-independent-final-rescored-1802-v1.json';s_path=d/'rgb-independent-final-statistics-1802-v1.json';audit=json.loads(a_path.read_text());s=json.loads(s_path.read_text())
 assert audit['status']=='verified_complete' and audit['physics_transitions']==796800 and len(audit['audits'])==16 and s['status']=='complete'
 out=d/'release-rgb-fresh300-independent-20260923T1927-v2';out.mkdir(exist_ok=False);prefix='wuji-rgb-frozen-fresh300-independent-20260923'
 shutil.copyfile(s_path,out/(prefix+'-statistics.json'));shutil.copyfile(a_path,out/(prefix+'-all-trial-audit.json'))
 fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
 for ax,sec in zip(axes,[2,5]):
  for model,offset,color,label in [('baseline',-.18,'tab:blue','Original RGB'),('mixed',.18,'tab:orange','Mixed RGB')]:
   c=s['conditions'][f'{model}-{sec}s'];groups=[c['fresh300']]+c['trained_grasp_groups']+[c['reused_fourth32']]
   values=np.array([x['rate']*100 for x in groups]);interval=np.array([x['wilson95'] for x in groups]).T*100
   xpos=np.arange(5)+offset;ax.bar(xpos,values,width=.34,label=label,color=color)
   ax.errorbar(xpos,values,yerr=np.maximum(np.stack([values-interval[0],interval[1]-values]),0),fmt='none',ecolor='black',elinewidth=1,capsize=3)
   for x,item in zip(xpos,groups):ax.text(x,item['wilson95'][1]*100+2,f"{item['success']}",ha='center',fontsize=9)
  ax.set(title=f'{sec}s external commands',xticks=range(5),xticklabels=['Fresh total\nn=300','Grasp A\nn=100','Grasp B\nn=100','Grasp C\nn=100','Old fourth\nn=32'],ylim=(-1,112),ylabel='All endpoints + body success (%)');ax.grid(axis='y',alpha=.2)
 handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2)
 fig.suptitle('New reset perturbations: success counts and 95% Wilson intervals')
 fig.savefig(out/(prefix+'-success-and-intervals.png'),dpi=180);fig.savefig(out/(prefix+'-success-and-intervals.pdf'));plt.close(fig)
 lines=['Frozen RGB policies: completed independent reset-cohort evaluation','',
  'All 16 conditions, 796800 physics transitions, raw trace rescoring, normal process exits,',
  'model hashes, cohort hashes, command timing and prediction/physics alignment verified.',
  'No fitting, model change or peak selection took place after this cohort was generated.','']
 for model in ['baseline','mixed']:
  lines.append(model+' passed both preregistered working thresholds: '+str(s['passed_both_preregistered_clocks'][model]))
  for sec in [2,5]:
   c=s['conditions'][f'{model}-{sec}s'];v=c['fresh300'];groups=c['trained_grasp_groups'];four=c['reused_fourth32']
   lines.append(f"  {sec}s: {v['success']}/{v['trials']} ({100*v['rate']:.2f}%), Wilson95 [{100*v['wilson95'][0]:.2f}, {100*v['wilson95'][1]:.2f}]%; groups "+'/'.join(str(x['success']) for x in groups)+f" of100; old fourth {four['success']}/32.")
 for sec,delta in s['paired_comparisons'].items():lines.append(f"Mixed-original {sec}s: {100*delta['mixed_minus_baseline_rate']:.2f} percentage points, paired stratified bootstrap95 "+str([round(100*x,3) for x in delta['stratified_paired_bootstrap95']])+'.')
 lines+=['','Working criteria were preregistered: >=95% across300 and >=90% in each of three',
  'trained grasp groups, separately for both clocks. Wilson lower bounds are reported,',
  'not required to exceed95%. Bootstrap uses10000 paired, grasp-stratified resamples.',
  'Both-clock same-state success is descriptive, not a posthoc acceptance criterion.','',
  'Scope: 3 trained grasp families x100 NEW, unfiltered reset perturbations, generated',
  'after both final5000 estimators were frozen. Same147x19x11mm knife and fixed camera.',
  'Per-axis position +/-0.5mm, joints +/-0.01rad, rotation-vector components +/-0.5deg.',
  'The fourth32 rows are the reused failure control, not independent unseen grasps.',
  'This does not establish new-grasp, new-geometry, wider-perturbation, camera or hardware',
  'transfer. Exact reset-known geometry and uncalibrated simulation physics are assumed.','',
  'Strict20s protocol:30Hz control/120Hz physics, alternate commands every2s or5s.',
  'Each command final9frames must all be within2mm; body displacement remains below',
  '10mm and rotation below0.25rad throughout; invalid/dead episodes fail.',
  'The frozen CNN uses RGB plus encoders/initial geometry/external commands to estimate',
  'body translation/rotation and slider. Causal finite differences produce velocity.',
  'The frozen actor receives these estimates, never current object/contact truth.',
  'At t0 only declared reset-known geometry is used. The independent cohort used the',
  'original local4090 evaluation pin and has not been migrated to H100.','',
  'The complete ZIP includes all16 rollouts and diagnostic images, the cohort and frozen',
  'visual weights, teacher actor, exact source archives, preregistration, full audits',
  'and finalization code. It is sufficient to replay this evaluation; training datasets',
  'are separately published in the original/mixed-development Release packages.','']
 (out/(prefix+'-README.txt')).write_text('\n'.join(lines))
 archive=out/(prefix+'-complete-evidence.zip');added=set();spec=json.loads((run/'status.json').read_text())['spec'];cohort=g/'rgb-fresh300-total-paired-seed20261120-v2'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  def add(p,name):
   assert p.is_file() and name not in added,(p,name);z.write(p,name);added.add(name)
  for folder,base in [(run,'evaluation'),(cohort,'cohort'),(final,'finalization')]:
   for p in sorted(folder.rglob('*')):
    if p.is_file() and not p.is_symlink():add(p,base+'/'+str(p.relative_to(folder)))
  source=spec['source']
  for key in ['archive','manifest']:
   p=r/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256'];add(p,'source/'+p.name)
  finalspec=f['spec'];p=r/finalspec['source_archive'];assert hashlib.sha256(p.read_bytes()).hexdigest()==finalspec['source_sha256'];add(p,'source/'+p.name)
  for p in [a_path,s_path,g/'rgb-fresh-paired-1703-proposal.json',g/'rgb-independent-paired-1729-v1-spec.json',g/'rgb-finalization-1802-v1-spec.json',g/'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',Path(__file__)]:add(p,'inputs/'+p.name)
  add(out/(prefix+'-README.txt'),'README.txt')
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 reassembler='reassemble-wuji-rgb-fresh300-independent-20260923.py';shutil.copyfile(d/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/reassembler)
 manifest=split_archive(archive,out/'parts',reassembler)
 files=sorted(p for p in out.rglob('*') if p.is_file() and p!=archive)
 (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
 (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),archive=manifest),indent=2)+'\n');print(out)
if __name__=='__main__':main()
