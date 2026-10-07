"""Task-specific saved actual states and native contacts; no visual acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_flat_table_event import record

def check(trial, duration):
    z = np.load(trial/'trace.npz'); t = z['time']+duration
    report = json.loads((trial/'report.json').read_text())
    g = KnifeGeometry(Path(report['physical_asset']).parent/'spec.json')
    k = G2Kinematics(); h = WujiKinematics()
    q = np.c_[z['arm_q'],z['q']]
    margin = np.minimum(q-np.r_[k.lower,h.lower],np.r_[k.upper,h.upper]-q)
    i,j = np.unravel_index(margin.argmin(),margin.shape)
    clear = []
    for index in range(len(t)):
        O = transform(z['object'][index,:3],z['object'][index,3:7])
        V = np.concatenate([p['vertices'] for p in g.collision_parts(z['slider'][index])])
        clear.append(float((V@O[:3,:3].T+O[:3,3])[:,2].min()-.75))
    native = [json.loads(line) for line in (trial/'wrap-contact-physical-steps.jsonl').open()]
    watch_start=8. if t.max()>=8. else float(t[0])
    air = [r for r in native if r['time_s']+duration>=watch_start-1e-6]
    lost = [r['time_s']+duration for r in air if not any(c['knife_link']=='link_0' and not c['hand_link'].startswith('hand_r_thumb') for c in r['contacts'])]
    pair = [json.loads(line) for line in (trial/'knife-contact-pairs.jsonl').open()]
    bad = [r for r in pair if any(n in ('link_0','link_1') for n in [r['body0'],r['body1']]) and any(n not in ('link_0','link_1','table') and not n.startswith('hand_r_') for n in [r['body0'],r['body1']])]
    obstacle = trial/'hand-obstacle-contact-pairs.jsonl'
    obs = [json.loads(line) for line in obstacle.open()] if obstacle.exists() else []
    result = dict(source_trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),
        all_saved_actual_frames=len(t),actual_min_joint_margin_rad=float(margin.min()),
        actual_arm_min_margin_rad=float(margin[:,:7].min()),actual_hand_min_margin_rad=float(margin[:,7:].min()),
        actual_thumb_min_margin_rad=float(margin[:,-4:].min()),
        worst_elapsed_s=float(t[i]),worst_joint=(k.names+h.names)[j],
        support_watch_start_elapsed_s=watch_start,
        knife_air_min_clearance_from8s_m=float(np.array(clear)[t>=watch_start-1e-6].min()),
        native_nonthumb_support_missing_steps_from8s=len(lost),first_missing_nonthumb_elapsed_s=lost[0] if lost else None,
        knife_other_robot_contact_records=len(bad),
        hand_table_contact_records=len([r for r in obs if 'table' in [r['body0'],r['body1']]]),
        native_axial_total_force_N=None,real_robot_ran=False,visual_accepted=False,
        scope='All saved actual states30Hz; knife carrier records240Hz; hand-obstacle pairs30Hz. No continuous interframe geometry certificate; no hardware claim.')
    (trial/'episode-actual-evidence.json').write_text(json.dumps(result,indent=2))
    record('direct_episode_actual_checked',[str(trial/'episode-actual-evidence.json')],config=result,
           next_step='Combine actual/native evidence with whole timeline visual; repair first meaningful failed constraint before local generalization')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--duration',type=float,required=True);a=p.parse_args();print(json.dumps(check(a.trial,a.duration)))
