"""Run the frozen nominal continuous G2/Wuji simulation; never hardware actions.

The selected weight is a native functional demo candidate, not a certificate of
necessary generalization. Optional initial-estimate adaptation recertifies the
actual acquisition/transfer and full commanded thumb path before simulation.
A physical asset is supplied only to the simulator; no asset ID selects policy.
"""
import argparse,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
B=Path('runs/wrap-force-20261004')

def run(args):
    subprocess.run([sys.executable,'-m']+args,cwd=R,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--initial-estimate',type=Path)
    p.add_argument('--knife-asset',type=Path,help='Physical simulator asset only')
    a=p.parse_args();out=a.output.resolve();assert not out.exists()
    frozen=json.loads((R/'research/wrap-force-20261004/FROZEN-CONTINUOUS-CANDIDATE-V10.json').read_text())
    cmd=json.loads((R/frozen['command']).read_text())
    if isinstance(cmd,dict):cmd=cmd['command']
    cmd=cmd[cmd.index('scripts.run_g2_robust_demo')+1:]
    cmd[cmd.index('--output')+1]=str(out/'simulation')
    if a.initial_estimate:
        prepared=out/'initial-preparation'
        run(['scripts.adapt_wuji_continuous_initial_geometry','--estimate',str(a.initial_estimate.resolve()),'--pickup-plan',cmd[cmd.index('--grasp-plan')+1],'--operation-plan',str(B/'continuous/source2-fixed-support-v1/operation-plan.json'),'--reference',cmd[cmd.index('--thumb-reference-override')+1],'--transfer',cmd[cmd.index('--postlift-regrasp')+1],'--acquisition',cmd[cmd.index('--acquisition-path')+1],'--localization',cmd[cmd.index('--table-calibration')+1],'--output',str(prepared)])
        transfer=json.loads((prepared/'transfer.json').read_text());plan=json.loads((prepared/'operation-plan.json').read_text());plan['post_lift_close_q']=transfer['hand_q'][-1];(prepared/'operation-audit-plan.json').write_text(json.dumps(plan,indent=2))
        run(['scripts.audit_g2_anchored_thumb_motor','--reference',str(prepared/'reference.json'),'--motor-plan',str(prepared/'operation-audit-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','81','--output',str(prepared/'full-stroke-audit.json')])
        for flag,name in [('--grasp-plan','pickup-plan.json'),('--thumb-reference-override','reference.json'),('--postlift-regrasp','transfer.json'),('--acquisition-path','acquisition.json'),('--table-calibration','localization.json')]:cmd[cmd.index(flag)+1]=str(prepared/name)
    else:out.mkdir(parents=True)
    if a.knife_asset:cmd+=['--knife-asset',str(a.knife_asset.resolve())]
    (out/'command.json').write_text(json.dumps([sys.executable,'-m','scripts.run_g2_robust_demo']+cmd,indent=2))
    run(['scripts.run_g2_robust_demo']+cmd)
    run(['scripts.evaluate_wuji_antirotation','--trial',str(out/'simulation')])
    run(['scripts.analyze_wuji_wrap_contacts','--trial',str(out/'simulation')])

if __name__=='__main__':main()
