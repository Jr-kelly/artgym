"""Replay actual encoder samples through current core; diagnostic only, not a task rollout."""
import isaacgym
import json
from pathlib import Path
import numpy as np
from scripts.wuji_rear_controller import RearController,load_bundle,ROOT
from scripts.run_wuji_rear_sim import smooth
from scripts.record_wuji_rear_event import record
s=load_bundle('research/rear-sim2real-20261009/bundle-deploy-v7.json');c=RearController(s);c.seed_issued(s['open_q_rad']);p=ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6';rows=[json.loads(l) for l in (p/'commands.jsonl').read_text().splitlines()];errors=[];push=s['release_seconds']+s['settle_seconds']
for row in rows:
    q=np.array(row['measured_q_rad']);t=row['time_s'];c.observe(q)
    if t<s['prepare_seconds']:raw=c.propose_hold(np.array(s['open_q_rad'])+smooth(t/s['prepare_seconds'])*(np.array(s['hold_target_rad'])-np.array(s['open_q_rad'])))
    elif t<push:
        if t>=s['release_seconds']+s['prewarm_after_release_seconds'] and not c.taken:c.takeover(q)
        raw=c.propose_hold(s['hold_target_rad'])
    else:raw=c.propose_push(q,t-push)
    sent=c.constrain(raw);c.commit(sent);errors.append(float(np.abs(sent-np.array(row['issued_target_rad'])).max()))
r=dict(scope='Current controller legal-input replay vs exact v6 video issued commands; offline parity, no new physics/hardware success',frames=len(rows),maximum_sent_error_rad=max(errors),passed=max(errors)<2e-6,real_robot_ran=False)
(ROOT/'research/rear-sim2real-20261009/v2/COMMAND-PARITY.json').write_text(json.dumps(r,indent=2));record('current_source_video_command_parity',[ROOT/'research/rear-sim2real-20261009/v2/COMMAND-PARITY.json'],r);print(json.dumps(r));assert r['passed']
