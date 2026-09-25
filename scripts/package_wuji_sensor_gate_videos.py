"""Package the completed autonomous sensor-runtime gates with actual no-text videos."""
from pathlib import Path
import hashlib,json,shutil,zipfile

def main():
 r=Path(__file__).resolve().parents[1];d=r/'runs/wuji-goal/diagnostics';run=d/'rgb-sensor-autonomous-driver-1823-v4';s=json.loads((run/'status.json').read_text());assert s['status']=='completed' and all(x['returncode']==0 for x in s['stages'])
 audit=d/'rgb-sensor-autonomous-gates-rescored-1837-v1.json';a=json.loads(audit.read_text());assert a['status']=='verified_runtime_gates' and a['physics_transitions']==5400
 out=d/'release-sensor-autonomous-three-gates-20260923T1900-v1';out.mkdir(exist_ok=False);prefix='wuji-sensor-autonomous-three-old-states-20260923'
 for stage in ['runtime-baseline-2s','runtime-mixed-2s','runtime-mixed-5s']:
  label=stage.replace('runtime-','');shutil.copyfile(run/stage/'policy-no-text.mp4',out/(prefix+'-'+label+'-no-text.mp4'));shutil.copyfile(run/(stage+'-contact-sheet.png'),out/(prefix+'-'+label+'-frames-no-text.png'))
 shutil.copyfile(audit,out/(prefix+'-trajectory-audit.json'))
 (out/(prefix+'-README.txt')).write_text('''Wuji autonomous sensor-runtime: three OLD initial-state gates

Each video is an actual 20-second PhysX control rollout, with 599 pre-action
RGB frames at 30 fps. There is no text overlay, scripted joint trajectory,
kinematic replay, current object truth input, or hardware connection. The
three views are source/functional16/functional15 old initial states. All three
states pass the full timing and body-retention criteria in each condition:
original RGB with 2-second commands, mixed RGB with 2-second commands, and
mixed RGB with 5-second commands. Full 5400-transition raw audit is included.

The sensor runtime takes camera images, joint encoders, URDF forward
kinematics, external goal commands, and exact reset-known geometry. It owns
its previous actions/targets. The frozen visual estimator predicts object
translation, rotation and slider position; causal finite differences estimate
slider velocity. A frozen RL actor outputs 20 actions; the resulting joint
targets are applied to physics. A second actor compares numerical outputs;
its outputs do not drive physics. The reference comparison tolerances were
2e-5 for observations/state and 2e-4 for action/target; actual action-to-target
mapping is separately checked below 1e-6. All three processes exit normally.

These are runtime/development gates on three previously used states, not an
independent reliability or real-hardware result. The separate 332-state port
validation first failed at step26 on a small action difference from different
FK inputs and recurrent histories. That failure is preserved separately and
must not be described as a passed large-scale port test. Independent frozen
RGB reliability evaluation is a separate ongoing experiment.

Knife geometry is 147 x 19 x 11 mm, mass35g, joint travel50mm and commanded
stroke40mm. Runtime assumes a calibrated fixed camera, accurate initial
geometry, 30Hz control and simulator actuator/physical properties. Camera,
encoder, force/friction/damping and reset measurement calibration on hardware
remain outstanding. The simplified gray knife is the actual training asset.

This package contains all three complete rollout folders, audit, source pin,
frozen actor and both frozen visual estimators, initial states, and this exact
packaging source. The video montage contains no annotations; filenames and
this README explain the conditions. No model was fitted or selected from
these three runtime gates.
''')
 source=s['spec']['source'];archive=out/(prefix+'-complete-evidence.zip');added=set()
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  def add(p,name):
   assert p.is_file() and name not in added,(p,name);z.write(p,name);added.add(name)
  for p in sorted(run.rglob('*')):
   if p.is_file() and not p.is_symlink():add(p,'rollouts/'+str(p.relative_to(run)))
  for key in ['archive','manifest']:
   p=r/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256'];add(p,'source/'+p.name)
  for name in ['rgb-state-fitting-1537-v2','rgb-mixed-fitting-1705-v1']:
   for suffix in ['.pth','.json']:add(d/name/'fitting'/('rgb-update5000'+suffix),'models/'+name+'/rgb-update5000'+suffix)
  for p in [r/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',r/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy',r/'runs/wuji-goal/bridge3-evaluation-states/manifest.json',audit,Path(__file__),r/'scripts/audit_wuji_rgb_policy_results.py']:
   add(p,'inputs/'+p.name)
  for p in out.glob('*README.txt'):add(p,'README.txt')
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 paths=sorted(p for p in out.iterdir() if p.is_file());manifest={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
 (out/(prefix+'-manifest.json')).write_text(json.dumps(dict(scope='Completed3oldstate gates; not independent orhardware',assets=manifest,source=source),indent=2)+'\n')
 (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),assets=len(manifest)+1,archive_sha256=manifest[archive.name]['sha256']),indent=2)+'\n');print(out)
if __name__=='__main__':main()
