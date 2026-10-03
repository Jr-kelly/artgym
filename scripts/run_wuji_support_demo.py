"""Portable simulation entrypoint: once-initial estimate -> continuous TABLE demo.

The estimate planner receives no simulator asset identity. The selected asset
is supplied separately to physics. This program never connects to a robot.
"""
import argparse,json,pathlib,subprocess,sys
from scripts.plan_wuji_initial_geometry import adapt

R=pathlib.Path(__file__).resolve().parents[1]
D=R/'research/support-pressure-20261003';OLD=R/'research/robust-knife-family-20261003'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--estimate',type=pathlib.Path,required=True)
    p.add_argument('--checkpoint',type=pathlib.Path,required=True)
    p.add_argument('--knife-asset',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--video',action='store_true')
    p.add_argument('--pressure-config',type=pathlib.Path)
    p.add_argument('--stroke-support',action='store_true',help='Development candidate, not established improvement')
    p.add_argument('--support-layout',choices=['original','brace','staged'],default='original',help='Public-estimate contact planning: original or experimental postlift brace/withdraw-cross-recontact. Label planning fallbacks; never uses physicalasset ID.')
    p.add_argument('--load',type=float,default=.5);p.add_argument('--detent',type=float,default=.5)
    p.add_argument('--load-profile',choices=['constant','sinusoidal','triangular','pulse'],default='pulse')
    p.add_argument('--load-frequency',type=float,default=2.9)
    p.add_argument('--hand-friction',type=float,default=.8);p.add_argument('--knife-friction',type=float,default=2.4)
    p.add_argument('--noise',type=float,default=.002);p.add_argument('--bias',type=float,default=.006)
    p.add_argument('--delay-frames',type=int,choices=[0,1],default=1)
    p.add_argument('--seed',type=int,default=2026100358)
    a=p.parse_args();output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    estimate=json.loads(a.estimate.read_text())
    values=adapt(estimate,json.loads((OLD/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text()),
                 json.loads((D/'coordinated-preload-moderate-v6.json').read_text()),
                 json.loads((OLD/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text()))
    motor,support,reference,audit=values
    if a.support_layout!='original':
        from scripts.plan_wuji_braced_support import plan,staged_transfer
        original_support=support
        transfer_audit=dict(requested=a.support_layout,brace_fallback=False,staged_fallback=False,
            scope='Shared rule based only on public-estimate IK/static planning; every physicalattempt retained, no currenttruth or physicalasset selection')
        try:
            support,reference=plan(motor,support,reference,output/'brace-plan',OLD/'functional-side-edge-under-support-v6/localization.json')
            if a.support_layout=='staged':
                try:support=staged_transfer(motor,original_support,support)
                except (AssertionError,ValueError) as error:
                    transfer_audit.update(staged_fallback=True,staged_failure=str(error))
        except (AssertionError,ValueError) as error:
            transfer_audit.update(brace_fallback=True,brace_failure=str(error))
        (output/'support-transfer-audit.json').write_text(json.dumps(transfer_audit,indent=2))
    if a.stroke_support:
        from scripts.plan_wuji_stroke_support import adapt_stroke_support
        reference,stroke_audit=adapt_stroke_support(motor,reference)
        (output/'stroke-support-audit.json').write_text(json.dumps(stroke_audit,indent=2))
    for name,value in zip(['motor-plan.json','support.json','reference.json','initial-estimate-audit.json'],[motor,support,reference,audit]):
        (output/name).write_text(json.dumps(value,indent=2))
    cmd=[sys.executable,'-m','scripts.run_g2_robust_demo','--output',str(output/'continuous'),
         '--grasp-plan',str(output/'motor-plan.json'),'--support-pressure-config',str(output/'support.json'),
         '--thumb-reference-override',str(output/'reference.json'),'--knife-asset',str(a.knife_asset.resolve()),
         '--residual-checkpoint',str(a.checkpoint.resolve()),'--seconds','36','--dx=-.1985','--dy=.05','--yaw=0',
         '--slider-face','up','--table-calibration',str(OLD/'functional-side-edge-under-support-v6/localization.json'),
         '--acquisition-path',str(OLD/'functional-side-edge-under-support-lateral-v3/acquisition-path.json'),
         '--handover-calibration',str(OLD/'handover-from-v25-v1.json'),
         '--load',str(a.load),'--detent',str(a.detent),'--load-profile',a.load_profile,'--load-frequency',str(a.load_frequency),
         '--hand-friction',str(a.hand_friction),'--knife-friction',str(a.knife_friction),
         '--observation-noise',str(a.noise),'--observation-bias',str(a.bias),'--seed',str(a.seed),
         '--actuation-delay-frames',str(a.delay_frames),'--pair-force-measurement','--resistance-integration','solver-brake']
    if a.video:cmd+=['--video']
    if a.pressure_config:cmd+=['--proprioceptive-pressure-config',str(a.pressure_config.resolve())]
    (output/'command.json').write_text(json.dumps(dict(command=cmd,scope='Simulation only; initial estimate synthesized/measured externally. Physical asset never supplied to planner; no robot interface.'),indent=2))
    raise SystemExit(subprocess.call(cmd,cwd=R))


if __name__=='__main__':main()
