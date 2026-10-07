"""Actual trajectory/contact evidence for this task; numbers do not accept video."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_flat_table_event import record

def evaluate(trial, start, end, hold=1., prefix=0.):
    z = np.load(trial / 'trace.npz')
    t = z['time'] + prefix
    report = json.loads((trial/'report.json').read_text())
    geometry = KnifeGeometry(Path(report['physical_asset']).parent/'spec.json')
    clear = []
    for i in range(len(t)):
        O = transform(z['object'][i,:3], z['object'][i,3:7])
        V = np.concatenate([p['vertices'] for p in geometry.collision_parts(float(z['slider'][i]))])
        clear.append(float((V @ O[:3,:3].T + O[:3,3])[:,2].min() - .75))
    window = (t >= start-1e-6) & (t <= end+1e-6)
    holding = window & (t >= end-hold-1e-6)
    baseline = float(z['slider'][np.argmin(abs(t-start))])
    displacement = z['slider'] - baseline
    native = [json.loads(l) for l in (trial/'wrap-contact-physical-steps.jsonl').open()
              if start-1e-6 <= json.loads(l)['time_s']+prefix <= end+1e-6]
    contact = []
    for r in native:
        pad = [c for c in r['contacts'] if c['hand_link']=='hand_r_thumb_pad_link' and c['knife_link']=='link_1']
        housing = [c for c in r['contacts'] if c['hand_link'].startswith('hand_r_thumb') and c['hand_link']!='hand_r_thumb_pad_link' and c['knife_link']=='link_1']
        support = [c for c in r['contacts'] if not c['hand_link'].startswith('hand_r_thumb') and c['knife_link']=='link_0']
        contact.append(dict(time_s=r['time_s']+prefix, pad=bool(pad), housing=bool(housing), support=bool(support),
                            normal_N=sum(c['normal_magnitude_N'] for c in pad),
                            normal_axial_component_N=sum(c['force_normal_contribution_knife_N'][2] for c in pad)))
    table = sum('table' in [r['body0'],r['body1']] for r in map(json.loads,(trial/'knife-contact-pairs.jsonl').open())
                if start <= r['time_s']+prefix <= end)
    k = G2Kinematics(); h = WujiKinematics(); physics=json.loads((trial/'physics.json').read_text())
    effort=np.array(physics['effort_limit'] if 'effort_limit' in physics else physics['effort'])
    q=np.c_[z['arm_q'],z['q']]; lo=np.r_[k.lower,h.lower]; hi=np.r_[k.upper,h.upper]
    result=dict(push_elapsed_s=[start,end],hold_s=hold,baseline_slider_m=baseline,
        max_active_displacement_m=float(displacement[window].max()),
        last_hold_min_active_displacement_m=float(displacement[holding].min()),
        last_hold_slider_range_m=float(np.ptp(z['slider'][holding])),
        min_whole_clearance_m=float(np.array(clear)[window].min()),table_contact_records=table,
        actual_joint_margin_rad=float(np.minimum(q[window]-lo,hi-q[window]).min()),
        peak_effort_fraction=float((abs(z['torque'][window])/effort[:27]).max()),
        native_physical_steps=len(contact),
        native_pad_slider_fraction=float(np.mean([r['pad'] for r in contact])),
        native_nonthumb_support_fraction=float(np.mean([r['support'] for r in contact])),
        native_thumb_housing_slider_fraction=float(np.mean([r['housing'] for r in contact])),
        actual_thumb_pad_normal_N_mean=float(np.mean([r['normal_N'] for r in contact])),
        native_total_axial_force_N=None,axial_force_status='Unavailable; normal contributions and brake reference are not total axial traction',
        source_trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),
        restored_development=(trial/'recorded-initialization.json').exists(),
        action_quality_accepted=False,real_robot_ran=False)
    result['mechanism_metrics_pass']=bool(result['last_hold_min_active_displacement_m']>.02 and table==0
        and result['min_whole_clearance_m']>.02 and result['native_nonthumb_support_fraction']==1
        and all(r['pad'] for r in contact if r['time_s']>=end-hold))
    (trial/'direct-stroke-evaluation.json').write_text(json.dumps(result,indent=2))
    (trial/'direct-stroke-contact-series.json').write_text(json.dumps(contact))
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--push-start',type=float,default=0);p.add_argument('--end',type=float,required=True)
    p.add_argument('--prefix-duration',type=float,default=0);a=p.parse_args()
    result=evaluate(a.trial,a.push_start,a.end,prefix=a.prefix_duration);print(json.dumps(result))
    record('direct_stroke_actual_evaluation',[str(a.trial/'direct-stroke-evaluation.json')],config=result,
        next_step='Actual divergence determines correction; short pass permits continuous fresh route, never accepts video from metrics alone')
