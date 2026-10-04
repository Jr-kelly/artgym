"""One fixed750 held-reset comparison. No continuous-pickup or mechanical proof claim."""
import argparse,json,sys,subprocess,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform

R=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['source0','source1','source2','source3','current','front-pad'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--video',action='store_true');a=p.parse_args()
    base=R/'runs/wrap-force-20261004';dx='-.1985'
    if a.case.startswith('source'):
        folder=base/'comparison/four-sources-v1'/a.case
        plan=folder/'motor-plan.json';ref=folder/'reference.json';loc=folder/'localization.json';arm=folder/'arm-seed.json';cal=folder/'handover-calibration.json'
    elif a.case=='front-pad':
        plan=base/'planning/front-pad-impedance-v1/motor-plan.json';ref=plan.parent/'reference.json';loc=base/'planning/front-pad-held-v1/localization.json';arm=loc.parent/'arm-seed.json';cal=None;dx='-.192'
    else:
        plan=R/'runs/antirotation-grasp-20261004/initial-geometry-v2/projected-00/motor-plan.json';ref=plan.parent/'reference-v1.json';loc=R/'runs/antirotation-grasp-20261004/pickup-plans-v1/opposed/localization.json';arm=loc.parent/'arm-seed.json';cal=R/'runs/antirotation-grasp-20261004/continuous-plans-v6/lower-side-calibrated/nominal-calibration.json'
    assert json.loads(ref.read_text())['all_feasible']
    assert np.isclose(json.loads(ref.read_text())['rows'][-1]['shift_m'],.04)
    assert (base/'comparison/four-sources-v1/native-mapping-report.json').exists()
    assert json.loads((base/'comparison/four-sources-v1/native-mapping-report.json').read_text())['passed']
    if cal is None:
        j=json.loads(plan.read_text());relative=np.linalg.inv(np.asarray(j['wrist_in_knife']));cal=plan.parent/'matched-initial-calibration.json'
        if not cal.exists():cal.write_text(json.dumps(dict(object_in_wrist=relative.tolist(),slider_in_wrist=(relative@transform([0,.0075,.010624586881962734-.03267458688196273])).tolist(),scope='Fixed nominal source-matched initial estimate; no live contact/object feedback'),indent=2)+'\n')
    checkpoint=R/'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth'
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d'
    cmd=[sys.executable,'-m','scripts.run_g2_robust_demo','--output',str(a.output),'--grasp-plan',str(plan),'--table-calibration',str(loc),'--held-diagnostic','--dx='+dx,'--dy=.05','--load','.2','--detent','.2','--hand-friction','.8','--knife-friction','1.8','--resistance-integration','solver-brake','--residual-checkpoint',str(checkpoint),'--thumb-reference-override',str(ref),'--handover-calibration',str(cal),'--wrap-contact-measurement']
    if arm.exists():cmd+=['--arm-seed',str(arm)]
    if a.video:cmd+=['--video']
    subprocess.run(cmd,check=True)
    subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_antirotation','--trial',str(a.output)],check=True)
    subprocess.run([sys.executable,'-m','scripts.analyze_wuji_wrap_contacts','--trial',str(a.output)],check=True)
    (a.output/'comparison-role.json').write_text(json.dumps(dict(case=a.case,scope=__doc__,fixed_checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),physics_hz=240,load_N=.2,detent_N=.2,full_command_span_m=.04,original_pool_expanded=False,matched_reference=str(ref),next='Interpret contacts/reference tracking and settled pose; usable candidates must be integrated into continuous pickup'),indent=2)+'\n')

if __name__=='__main__':main()
