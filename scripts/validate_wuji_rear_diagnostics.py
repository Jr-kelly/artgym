"""Small algorithm contracts with known bias/shift, not physical/hardware trials."""
from pathlib import Path
import json
import numpy as np
from scripts.analyze_wuji_rear_response import lag_scan
from scripts.wuji_rear_diagnostics import ShortProbe

def main():
    t=np.arange(210)/30.;u=np.zeros(len(t));u[30:]=.01*np.sin(np.arange(180)*.43)+.002*np.sin(np.arange(180)*.93)
    take=np.arange(40,180);checks={};examples=[]
    for added in [0,1]:
        q=u[np.maximum(np.arange(len(t))-1-added,0)]-.095
        a=lag_scan(t[take],t,u,q[take],.095,local=True);checks['known_shift_'+str(added)]=a['estimate_samples']==added;examples.append(a)
    a=lag_scan(t[take],t,np.zeros(len(t)),np.zeros(len(take))-.095,.095,local=True);checks['no_excitation_not_estimated']=a['estimate_samples'] is None
    a=lag_scan(t[take],t,u,u[take]-.095,.095,local=False);checks['closed_loop_not_identified']=a['estimate_samples'] is None
    clock=ShortProbe(.035,4);ts=np.arange(0,clock.start,1/30);checks['prefix_clock_exact']=all(clock.clock(x)==x for x in ts);checks['endpoint_frozen']=clock.clock(9)==clock.end
    eps=1e-5;checks['braking_rate_continuity']=abs((clock.clock(clock.start+eps)-clock.clock(clock.start))/eps-1)<1e-6 and abs((clock.clock(clock.finish)-clock.clock(clock.finish-eps))/eps)<1e-6
    # Independent saved physics: prefix commands exactly match already validated full v6.
    R=Path('runs/rear-sim2real-20261009');rows=lambda p:[json.loads(l) for l in (p/'commands.jsonl').read_text().splitlines()]
    full=rows(R/'final/nominal-video-v6');short=rows(R/'v2/probe-nominal');cut=3+3.666666666666667+clock.start
    errors=[max(abs(np.array(a['issued_target_rad'])-b['issued_target_rad'])) for a,b in zip(full,short) if a['time_s']<cut]
    checks['physical_recorded_prefix_same_commands']=max(errors)<2e-6
    checks={k:bool(v) for k,v in checks.items()}
    r=dict(checks=checks,passed=all(checks.values()),algorithm_signals_scope='30Hz rich synthetic signals with static95mrad offset and zero/one additional frame; not physical simulations',signal_lag_examples=examples,physics_command_prefix_max_error_rad=float(max(errors)),probe=clock.metadata(),real_robot_ran=False)
    Path('research/rear-sim2real-20261009/v2/DIAGNOSTIC-VERIFICATION.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['passed']
if __name__=='__main__':main()
