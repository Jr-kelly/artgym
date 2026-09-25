"""Publish complete port or wider-reset validation with all rows and exact evidence."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.summarize_wuji_rgb_independent import wilson
from scripts.package_wuji_dagger_final import split_archive

def main():
 p=argparse.ArgumentParser();p.add_argument('--kind',choices=['sensor','wider'],required=True);args=p.parse_args();r=Path(__file__).resolve().parents[1];g=r/'runs/wuji-goal';d=g/'diagnostics'
 if args.kind=='sensor':
  name='rgb-sensor-active-parity-development-1924-v1';auditname='rgb-sensor-active-final-rescored-1937-v1.json';prefix='wuji-sensor-port-all332-old-states-20260923';extras=['rgb-sensor-interface-parity-1807-v1','rgb-sensor-interface-parity-1812-v2','rgb-sensor-autonomous-driver-1817-v3','rgb-sensor-autonomous-driver-1823-v4','rgb-sensor-autonomous-development-chunks-1832-v1','rgb-sensor-discrepancy-1839-v1','rgb-sensor-discrepancy-1843-v2','rgb-sensor-matched-gpu2-gate-1903-v2','rgb-sensor-matched-gpu2-development-1903-v3','rgb-sensor-lifecycle-1918-v1','rgb-sensor-cpu-latency-1953-v1']
  notes='''The independent sensor runtime actually drives PhysX from RGB, encoder joints,
URDF FK, external commands and exact reset-known geometry. It owns action/target
and causal velocity history. No current object/contact truth enters the driver.
The reference actor is a numerical comparison on identical sensor/FK/estimated
inputs with its own recurrent history; its actions are not applied to physics.

Thresholds are2e-5 for observable/state comparisons and2e-4 for actor/target
comparisons, plus1e-6 for the actual action-to-target mapping. Assertions apply
to active episodes. Retired episodes retain failure status in task scoring;
their counts, IDs and raw differences are logged and independently checked.
The active mask is never passed to the driver. Before this lifecycle handling,
PhysX replaced a failed row's tips with cached reset values and cleared the
reference recurrent history, causing a meaningless post-retirement mismatch.
All failures and their exact source pins are included, not reclassified as passes.

This is a port-validation experiment on332 OLD development rows, not a fresh
independent cohort. The independently validated mixed RGB result is published
separately. The completed3-old-state videos in this bundle contain no text;
the earlier13-frame failed rollout is a failure artifact, not a successful demo.
The CPU latency subfolder is a fixed-input timing diagnostic, not a CPU task
success or hardware test. It excludes camera acquisition, transport and motors.
'''
 else:
  name='rgb-wider-reset-stress-1932-v2';auditname='rgb-wider-final-rescored-1940-v1.json';prefix='wuji-rgb-wider-reset-stress300-20260923';extras=[]
  notes='''The same frozen mixed RGB estimator and frozen RL actor are tested on300 NEW
unfiltered perturbations of three trained grasp families after the primary
independent evaluation completed. Reset range is twice the primary range:
position +/-1mm/axis, joints +/-0.02rad, rotation-vector components +/-1degree.
Seed20261123. Same knife, camera and physics. Fourth32 reuse the failure control.
This is a separately declared exploratory robustness test, not new-grasp,
new-geometry or hardware validation. No model/physics tuning or outcome filtering
was used. Initial-generation v1 failed before generating any states because its
candidate path omitted a directory; v2 corrected only that path, with v1 preserved.
'''
 run=d/name;state=json.loads((run/'status.json').read_text());assert state['status']=='completed' and all(s['returncode']==0 for s in state['stages']);auditpath=d/auditname;audit=json.loads(auditpath.read_text());assert audit['status']=='verified_complete' and audit['physics_transitions']==398400 and len(audit['audits'])==8
 out=d/('release-'+args.kind+'-complete-validation-20260923-v1');out.mkdir(exist_ok=False);shutil.copyfile(auditpath,out/(prefix+'-all-trial-audit.json'))
 fig,axes=plt.subplots(1,2,figsize=(10,4.8),layout='constrained');lines=[]
 for ax,sec in zip(axes,[2,5]):
  c=audit['conditions'][f'mixed-{sec}s'];groups=c['groups'];nums=[sum(x['joint'] for x in groups[:3])]+[x['joint'] for x in groups];dens=[300,100,100,100,32];values=np.array(nums)/dens*100;ci=np.array([wilson(n,t) for n,t in zip(nums,dens)]).T*100
  ax.bar(range(5),values,color='tab:orange',width=.6);ax.errorbar(range(5),values,yerr=np.maximum(np.stack([values-ci[0],ci[1]-values]),0),fmt='none',ecolor='black',capsize=3)
  for i,n in enumerate(nums):ax.text(i,ci[1,i]+2,str(n),ha='center',fontsize=9)
  ax.set(title=f'{sec}s commands',ylim=(-1,112),xticks=range(5),xticklabels=['Total\nn=300','A\nn=100','B\nn=100','C\nn=100','Old fourth\nn=32'],ylabel='All criteria success (%)');ax.grid(axis='y',alpha=.2)
  lines.append(f'{sec}s commands: {nums[0]}/300; three groups '+str(nums[1:4])+' of100; fourth '+str(nums[4])+'/32.')
 fig.suptitle(('Sensor runtime: all OLD development states' if args.kind=='sensor' else 'Frozen RGB: new perturbations at twice the reset range')+'\nSuccess counts and95% Wilson intervals');fig.savefig(out/(prefix+'-success.png'),dpi=180);fig.savefig(out/(prefix+'-success.pdf'));plt.close(fig)
 (out/(prefix+'-README.txt')).write_text(prefix+'\n\n'+'\n'.join(lines)+'\n\n'+notes+'''\nAll8 conditions and398400 transitions were independently rescored. Physics:
20s,30Hz control/120Hz simulation,2s/5s external alternating goals. Each stage
last9frames must all be within2mm; body remains within10mm/.25rad throughout;
invalid or retired episodes fail. All332 rows, including the fourth, remain.
Knife147x19x11mm, mass35g,50mm travel and40mm target. No real hardware validation.
The complete ZIP contains all rollouts, exact source pins, models, initial states,
audits, and relevant failures; the part manifest/reassembler verifies SHA256.
''')
 archive=out/(prefix+'-complete-evidence.zip');added=set();sources={}
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  def add(p,name):
   assert p.is_file(),p
   if name not in added:z.write(p,name);added.add(name)
  for folder in [run]+[d/n for n in extras]:
   assert folder.is_dir(),folder
   for p in sorted(folder.rglob('*')):
    if p.is_file() and not p.is_symlink():add(p,'runs/'+folder.name+'/'+str(p.relative_to(folder)))
   status=folder/'status.json'
   if status.exists():
    source=json.loads(status.read_text()).get('spec',{}).get('source')
    if source:sources[source['archive']]=source
  for source in sources.values():
   for key in ['archive','manifest']:
    p=r/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256'];add(p,'source/'+p.name)
  spec=state['spec'];initial=r/spec.get('initial_states',{}).get('path','runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')
  for p in initial.parent.glob('*'):
   if p.is_file() and p.suffix in ['.json','.npy']:add(p,'initial/'+p.name)
  for item in spec['artifacts'].values():
   p=r/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];add(p,'models/'+p.name);add(p.with_suffix('.json'),'models/'+p.with_suffix('.json').name)
  for p in [g/'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',auditpath,Path(__file__),r/'scripts/audit_wuji_rgb_policy_results.py']:add(p,'inputs/'+p.name)
  if args.kind=='sensor':
   for pattern in ['rgb-sensor-discrepancy-replay-*.json','rgb-sensor-retired-row-diagnosis-*.json','rgb-sensor-discrepancy-replay-*.log']:
    for p in d.glob(pattern):add(p,'diagnoses/'+p.name)
   add(r/'scripts/benchmark_wuji_sensor_cpu.py','inputs/benchmark_wuji_sensor_cpu.py')
  else:
   for p in [d/'rgb-wider-final-statistics-1940-v1.json',g/'rgb-wider-reset-stress-1932-proposal-v2.json',r/'scripts/prepare_wuji_wider_rgb_validation.py']:add(p,'inputs/'+p.name)
   for p in (g/'rgb-wider300-total-seed20261123-v1').glob('*'):add(p,'preparation-failure/'+p.name)
  add(out/(prefix+'-README.txt'),'README.txt')
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 script='reassemble-'+prefix+'.py';shutil.copyfile(d/'release-dagger-final-and-offline-parts-20260923T1557/reassemble-wuji-evidence-20260923.py',out/script);m=split_archive(archive,out/'parts',script)
 files=sorted(p for p in out.rglob('*') if p.is_file() and p!=archive);(out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files));(out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),archive=m),indent=2)+'\n');print(out)
if __name__=='__main__':main()
