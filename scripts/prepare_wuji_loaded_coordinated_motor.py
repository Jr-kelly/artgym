"""Prepare an acquired-load coordinated stroke and its focused geometry evidence.

No simulator state or physics parameter is changed. Native execution and actual
hand/contact inspection remain necessary after this planned-path check.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.record_wuji_flat_table_event import record


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--path', type=Path, required=True)
    p.add_argument('--servo-prior', type=Path, required=True)
    p.add_argument('--support-preload-prior', type=Path)
    p.add_argument('--release-acquired-thumb-body-contact', action='store_true')
    a = p.parse_args()
    d = json.loads(a.path.read_text()); out = a.path.parent
    source = Path(d['source']); s = np.load(source/'takeover.npz')
    c = json.loads(Path(d['candidate']).read_text())
    trial, native, end = source_contacts(source)
    materials = {}
    for name in c['support_materials']:
        contacts = [v for r in native for v in r['contacts']
                    if v['hand_link'] == name and v['knife_link'] == 'link_0']
        if not contacts:
            raise ValueError('No acquired contact for '+name)
        materials[name] = np.mean([v['position_hand_link_m'] for v in contacts], axis=0).tolist()
    for x in d['diagnostics']:
        x['expected_object_world'] = x['planned_object_world']
        x.setdefault('planned_support_materials', materials)
    base = out/'motor-for-load-transport.json'
    base.write_text(json.dumps(d, indent=2))
    specs = []
    for name, point in materials.items():
        first = 0 if '_index_' in name else 4 if '_middle_' in name else 12
        ids = list(range(first, first+4))
        acquired = float(abs(s['issued_target'][7:][ids]-s['robot_q'][7:][ids]).max())
        specs.append(dict(material_link=name, material_point=point, digit_indices=ids,
                          max_preload_rad=max(.1, acquired),
                          knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    carriers = out/'carriers.json'; carriers.write_text(json.dumps(specs, indent=2))
    for module, args in [
        ('scripts.apply_wuji_direct_damping_feedforward', ['--motor', str(base), '--physics', str(trial/'physics.json'), '--output', str(out/'motor-damping.json')]),
        ('scripts.prepare_wuji_direct_smooth_loaded_reference', ['--motor', str(out/'motor-damping.json'), '--source', str(source), '--carriers', str(carriers), '--physics', str(trial/'physics.json'), '--output', str(out/'motor-smooth-loaded.json')])]:
        subprocess.run([sys.executable, '-m', module]+args, check=True, stdout=subprocess.DEVNULL)
    motor = json.loads((out/'motor-smooth-loaded.json').read_text())
    servo = json.loads(a.servo_prior.read_text())['direct_pressure_path_servo']
    servo['material_point'] = c['thumb_material']
    if 'axial_proxy_reference_N' in c:servo['axial_reference_N']=c['axial_proxy_reference_N']
    motor['direct_pressure_path_servo'] = servo
    if a.support_preload_prior:
        prior = json.loads(a.support_preload_prior.read_text())['support_preload_servo']
        physics = json.loads((trial/'physics.json').read_text())
        support = {key: prior[key] for key in
                   ['gain', 'max_step_rad', 'max_correction_rad', 'activation_ramp_s']}
        references = [v['normal_reference_N'] for v in prior['carriers']]
        if not np.allclose(references, references[0]):
            raise ValueError('Current carriers require one common support reference')
        support['carriers'] = []
        if c.get('support_command_upper_margin_rad'):support['command_upper_margin_rad']=c['support_command_upper_margin_rad']
        for spec in specs:
            name = spec['material_link']
            forces = [v['force_normal_contribution_knife_N'] for r in native
                      for v in r['contacts'] if v['hand_link'] == name
                      and v['knife_link'] == 'link_0']
            direction = np.sum(forces, axis=0)
            direction /= np.linalg.norm(direction)
            ids = spec['digit_indices']
            support['carriers'].append(dict(
                material_link=name, material_point=spec['material_point'],
                digit_indices=ids,
                digit_kp=np.array(physics['kp'][7:])[ids].tolist(),
                normal_direction_knife=direction.tolist(),
                normal_reference_N=references[0]))
            support['carriers'][-1]['hold_acquired_joint_indices']=[
                index for index in c.get('preserve_acquired_spread_joint_indices',[])
                if index in ids]
            if name in c.get('slide_support_materials',[]):
                support['carriers'][-1]['material_point_path']=[dict(
                    time_s=row['time_s'], material_point=row['planned_support_materials'][name])
                    for row in motor['diagnostics']]
        motor['support_preload_servo'] = support
    for row in motor['rows']:
        for index in c.get('preserve_acquired_spread_joint_indices',[]):
            row['hand_q'][index]=float(s['issued_target'][7+index])
    command_upper=WujiKinematics().upper
    for row in motor['rows']:
        for key,margin in c.get('support_command_upper_margin_rad',{}).items():
            index=int(key);row['hand_q'][index]=min(row['hand_q'][index],float(command_upper[index]-float(margin)))
    final = out/'motor-native.json'; final.write_text(json.dumps(motor, indent=2))
    g = DigitGeometry(max_face_axes=10, knife_spec=Path(specs[0]['knife_spec']))
    k = G2Kinematics(); checker = HandIntersection()
    D = d['diagnostics']; times = np.array([x['time_s'] for x in D])
    hands = np.array([x['planned_hand_q'] for x in D]); arms = np.array([x['planned_arm_q'] for x in D])
    rows = []
    for t in np.arange(times[0], times[-1]+.0001, .25):
        h = np.array([np.interp(t, times, hands[:,j]) for j in range(20)])
        arm = np.array([np.interp(t, times, arms[:,j]) for j in range(7)])
        # These paths keep object orientation fixed. Reject an incompatible
        # path instead of checking against the wrong geometry.
        assert np.allclose([x['planned_object_world'] for x in D], D[0]['planned_object_world'])
        L = np.linalg.inv(np.array(D[0]['planned_object_world'])) @ k.forward(arm)
        slider = float(np.interp(t, times, [x['expected_slider_q_m'] for x in D]))
        gaps = g.gaps(h, L, slider, 'thumb')
        selected_gaps=[]
        for spec in c.get('selected_self_clearance',[]):
            pairs=g.self_gaps(h,'index',certify_clearance_m=spec['clearance_m'])
            pair=min((v for v in pairs if
                      {v['moving_link'],v['other_link']}==set(spec['links'])),
                     key=lambda v:v['gap_lower_bound_m'])
            selected_gaps.append(dict(links=spec['links'],
                gap_m=pair['gap_lower_bound_m'], requested_m=spec['clearance_m']))
        W=k.forward(arm);F=g.w.forward(h)
        table_clearance=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75)
                            for n,parts in g.meshes.items() for v,_ in parts)
        rows.append(dict(time_s=float(t), self=checker.inspect(h),
                         body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
                         housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!='hand_r_thumb_pad_link'),
                         hand_margin_rad=float(np.minimum(h-g.w.lower, g.w.upper-h).min()),
                         hand_table_clearance_m=table_clearance,
                         selected_self_gaps=selected_gaps))
    poses = np.c_[arms, hands]
    summary = dict(self_frames=sum(bool(x['self']) for x in rows),
                   body_gap_min_m=min(x['body_gap_m'] for x in rows),
                   housing_cap_gap_min_m=min(x['housing_cap_gap_m'] for x in rows),
                   maximum_planned_rate_rad_s=float((abs(np.diff(poses,axis=0))/np.diff(times)[:,None]).max()),
                   max_thumb_error_m=max(x['thumb_error_m'] for x in D),
                   max_support_error_m=max(max(x['support_errors_m'].values()) for x in D),
                   source_jump_rad=float(abs(np.r_[motor['rows'][0]['arm_q'],motor['rows'][0]['hand_q']]-s['issued_target']).max()),
                   minimum_hand_table_clearance_m=min(x['hand_table_clearance_m'] for x in rows),
                   scope='4Hz interpolated planned thumb body/housing and hand self checks; acquired nonthumb SAT gaps are not penetration depths; no dynamic acceptance')
    body_ok = summary['body_gap_min_m']>.0001
    if a.release_acquired_thumb_body_contact:
        # A genuine acquired root contact must be released by motor motion.
        # This permits its existing conservative SAT gap at entry; it does
        # not alter collision physics or treat SAT gaps as penetration depth.
        summary['acquired_body_gap_m'] = rows[0]['body_gap_m']
        summary['terminal_body_gap_m'] = rows[-1]['body_gap_m']
        summary['acquired_root_release_development'] = True
        body_ok = (summary['body_gap_min_m'] >= rows[0]['body_gap_m']-.00005
                   and rows[-1]['body_gap_m']>.0001)
    summary['geometry_permits_native'] = bool(summary['self_frames']==0 and body_ok and summary['housing_cap_gap_min_m']>.0001 and summary['max_thumb_error_m']<.0005 and summary['max_support_error_m']<.0008 and summary['source_jump_rad']<1e-6 and summary['minimum_hand_table_clearance_m']>.0002)
    if c.get('selected_self_clearance'):
        # Allow the acquired entry only; check the requested reserve after
        # the explicit separation ramp, with a 0.5mm optimization residual.
        summary['selected_self_reserve_deficit_max_m']=max(
            max(v['requested_m']-v['gap_m'],0.) for row in rows
            if row['time_s']>=(6.5 if c.get('synchronize_posture_transition') else 1.5) for v in row['selected_self_gaps'])
        summary['geometry_permits_native'] &= summary['selected_self_reserve_deficit_max_m']<.0005
    evidence = out/'dense-functional-guard.json'; evidence.write_text(json.dumps(dict(summary=summary, rows=rows), indent=2))
    e = record('loaded_coordinated_motor_geometry_evidence', [str(final), str(evidence)], config=summary,
               next_step='Passing geometry immediately native stroke; actual first failure changes the next mechanism')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:
        f.write('\n'+e['utc']+' '+str(out)+' '+json.dumps(summary)+'\n')
    print(json.dumps(summary))
    if not summary['geometry_permits_native']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
