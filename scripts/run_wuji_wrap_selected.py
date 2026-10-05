"""Run the frozen nominal continuous G2/Wuji simulation; never hardware actions.

The selected weight is a native functional demo candidate, not a certificate of
necessary generalization. Optional initial-estimate adaptation recertifies the
actual acquisition/transfer and full commanded thumb path before simulation.
A physical asset is supplied only to the simulator; no asset ID selects policy.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
B=Path('runs/wrap-force-20261004')

def run(args):
    subprocess.run([sys.executable,'-m']+args,cwd=R,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selection',type=Path,help='Explicit frozen command manifest; original default selection unchanged')
    p.add_argument('--load',type=float,help='Simulator brake capacity only; never a policy input')
    p.add_argument('--detent',type=float,help='Simulator start/groove capacity only')
    p.add_argument('--no-video',action='store_true')
    for name in ['hand-friction','knife-friction','observation-noise','observation-bias']:
        p.add_argument('--'+name,type=float,help='Explicit frozen-policy validation condition')
    p.add_argument('--actuation-delay-frames',type=int,choices=[0,1])
    p.add_argument('--load-profile',choices=['constant','sinusoidal','triangular','pulse'])
    p.add_argument('--seed',type=int)
    p.add_argument('--preset',choices=['wrap','source2'],default='wrap',
                   help='Frozen wrap corner pickup (default) or earlier source2 scheduled-hold fallback')
    p.add_argument('--initial-estimate',type=Path)
    p.add_argument('--knife-asset',type=Path,help='Physical simulator asset only')
    a=p.parse_args();out=a.output.resolve();assert not out.exists()
    freeze='FROZEN-WRAP-CONTINUOUS-CANDIDATE-V12.json' if a.preset=='wrap' else 'FROZEN-CONTINUOUS-CANDIDATE-V10.json'
    if a.selection:freeze=str(a.selection.resolve())
    frozen=json.loads((R/'research/wrap-force-20261004'/freeze).read_text())
    cmd=frozen['command'] if isinstance(frozen['command'],list) else json.loads((R/frozen['command']).read_text())
    if isinstance(cmd,dict):cmd=cmd['command']
    cmd=cmd[cmd.index('scripts.run_g2_robust_demo')+1:]
    weight=R/cmd[cmd.index('--residual-checkpoint')+1]
    expected=frozen.get('checkpoint_sha256',frozen.get('weight_sha256'))
    if expected:assert hashlib.sha256(weight.read_bytes()).hexdigest()==expected
    cmd[cmd.index('--output')+1]=str(out/'simulation')
    for flag,value in [('--load',a.load),('--detent',a.detent)]:
        if value is not None:
            assert value>=0
            cmd[cmd.index(flag)+1]=str(value)
    if a.no_video and '--video' in cmd:cmd.remove('--video')
    for name in ['hand-friction','knife-friction','observation-noise','observation-bias',
                 'actuation-delay-frames','load-profile','seed']:
        value=getattr(a,name.replace('-','_'))
        if value is not None:
            flag='--'+name
            if flag in cmd:cmd[cmd.index(flag)+1]=str(value)
            else:cmd += [flag,str(value)]
    if a.initial_estimate and a.preset=='wrap':
        prepared=out/'initial-preparation'
        run(['scripts.adapt_wuji_direct_corner_initial_geometry','--estimate',str(a.initial_estimate.resolve()),
             '--plan',cmd[cmd.index('--grasp-plan')+1],
             '--reference',cmd[cmd.index('--thumb-reference-override')+1],
             '--localization',cmd[cmd.index('--table-calibration')+1],'--output',str(prepared)])
        run(['scripts.plan_g2_functional_acquisition_path','--plan',str(prepared/'motor-plan.json'),
             '--localization',str(prepared/'localization.json'),'--knife-spec',str(prepared/'estimated-collision/spec.json'),'--table-y','-.23','--output',str(prepared/'acquisition')])
        run(['scripts.audit_wuji_actual_acquisition_motor','--plan',str(prepared/'motor-plan.json'),
             '--acquisition',str(prepared/'acquisition/acquisition-path.json'),'--table-y','-.23',
             '--output',str(prepared/'closure-audit.json')])
        run(['scripts.audit_g2_anchored_thumb_motor','--reference',str(prepared/'reference.json'),
             '--motor-plan',str(prepared/'motor-plan.json'),'--knife-spec',
             str(prepared/'estimated-collision/spec.json'),
             '--samples','81','--output',str(prepared/'full-stroke-audit.json')])
        for flag,name in [('--grasp-plan','motor-plan.json'),('--thumb-reference-override','reference.json'),
                          ('--acquisition-path','acquisition/acquisition-path.json'),
                          ('--table-calibration','localization.json'),('--handover-calibration','calibration.json')]:
            cmd[cmd.index(flag)+1]=str(prepared/name)
        # Same conservative placement rule for every noisy initial estimate.
        # This is body-root inset, not combined center of mass.
        for i,value in enumerate(cmd):
            if value.startswith('--dx='):cmd[i]='--dx=-.194'
    elif a.initial_estimate:
        prepared=out/'initial-preparation'
        run(['scripts.adapt_wuji_continuous_initial_geometry','--estimate',str(a.initial_estimate.resolve()),'--pickup-plan',cmd[cmd.index('--grasp-plan')+1],'--operation-plan',str(B/'continuous/source2-fixed-support-v1/operation-plan.json'),'--reference',cmd[cmd.index('--thumb-reference-override')+1],'--transfer',cmd[cmd.index('--postlift-regrasp')+1],'--acquisition',cmd[cmd.index('--acquisition-path')+1],'--localization',cmd[cmd.index('--table-calibration')+1],'--output',str(prepared)])
        transfer=json.loads((prepared/'transfer.json').read_text());plan=json.loads((prepared/'operation-plan.json').read_text());plan['post_lift_close_q']=transfer['hand_q'][-1];(prepared/'operation-audit-plan.json').write_text(json.dumps(plan,indent=2))
        run(['scripts.audit_g2_anchored_thumb_motor','--reference',str(prepared/'reference.json'),'--motor-plan',str(prepared/'operation-audit-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','81','--output',str(prepared/'full-stroke-audit.json')])
        for flag,name in [('--grasp-plan','pickup-plan.json'),('--thumb-reference-override','reference.json'),('--postlift-regrasp','transfer.json'),('--acquisition-path','acquisition.json'),('--table-calibration','localization.json')]:cmd[cmd.index(flag)+1]=str(prepared/name)
    else:out.mkdir(parents=True)
    if a.knife_asset:cmd+=['--knife-asset',str(a.knife_asset.resolve())]
    (out/'command.json').write_text(json.dumps([sys.executable,'-m','scripts.run_g2_robust_demo']+cmd,indent=2))
    (out/'selection.json').write_text(json.dumps(dict(preset=a.preset,freeze=freeze,
        actor_sha256=hashlib.sha256(weight.read_bytes()).hexdigest(),
        initial_estimate_scope='Once-estimated common geometry mechanism; physical asset supplied only to simulator',
        real_robot_ran=False,necessary_generalization_claim=False),indent=2))
    run(['scripts.run_g2_robust_demo']+cmd)
    run(['scripts.evaluate_wuji_antirotation','--trial',str(out/'simulation')])
    run(['scripts.analyze_wuji_wrap_contacts','--trial',str(out/'simulation')])

if __name__=='__main__':main()
