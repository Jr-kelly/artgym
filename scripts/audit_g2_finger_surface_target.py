"""Compare recorded pad contacts and export a reference, without simulation writes.

The reference is an operation endpoint for planning, never a continuous-state
reset. Contact occurrence/geometry is not a measurement of load or grip force.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

DIGITS = ['thumb', 'index', 'middle', 'ring', 'pinky']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run):
    t = np.load(run / 'trace.npz')
    ids = np.flatnonzero(t['phase'] == 'operate')
    assert len(ids) == 600 and np.all(np.diff(ids) == 1)
    rank = {int(step): i for i, step in enumerate(ids)}
    contacts = {finger: [] for finger in DIGITS}
    broad = np.zeros((600, 4), dtype=bool)
    for line in (run / 'knife-contact-pairs.jsonl').open():
        row = json.loads(line)
        if row['step'] not in rank:
            continue
        for side in [0, 1]:
            link = row['body%d' % side]
            other = row['body%d' % (1-side)]
            for finger in DIGITS:
                if link != 'hand_r_%s_pad_link' % finger:
                    continue
                point = np.array(row['localPos%d' % (1-side)])
                contacts[finger].append((row['step'], other, point))
                if finger != 'thumb' and other == 'link_0' and abs(point[1] + .004) <= .0003:
                    broad[rank[row['step']], DIGITS.index(finger)-1] = True
    rows = {}
    for finger, records in contacts.items():
        expected = 'link_1' if finger == 'thumb' else 'link_0'
        selected = [r for r in records if r[1] == expected]
        points = np.array([r[2] for r in selected])
        rows[finger] = dict(contact_link=expected,
            operation_contact_fraction=len(set(r[0] for r in selected))/600.,
            point_median_m=np.median(points, axis=0).tolist() if len(points) else None,
            point_min_m=points.min(0).tolist() if len(points) else None,
            point_max_m=points.max(0).tolist() if len(points) else None,
            width_edge_margin_median_m=float(np.median((.005 if finger == 'thumb' else .0095)-abs(points[:, 0]))) if len(points) else None)
    report = json.loads((run / 'report.json').read_text())
    result = dict(run=str(run),source_trace_sha256=sha(run/'trace.npz'),
        contact_log_sha256=sha(run/'knife-contact-pairs.jsonl'),frames=600,
        contact_order=DIGITS,contacts=rows,
        three_or_more_non_thumb_bottom_pad_fraction=float((broad.sum(1)>=3).mean()),
        four_non_thumb_bottom_pad_fraction=float((broad.sum(1)==4).mean()),
        bottom_face_diagnostic_tolerance_m=.0003,
        bottom_face_tolerance_scope='Classification around actual knife y=-4mm; not a new physical success or penetration threshold',
        endpoint_max_errors_m=[x['max_error_m'] for x in report['endpoints']],
        world_drift_max_m=report['world_drift_max_m'],
        world_rotation_max_rad=report['world_rotation_max_rad'],
        basic_10mm=report['basic_10mm'],strict_2mm=report['strict_2mm'],
        stable_world_10mm_025rad=report['stable_world_10mm_025rad'],
        initial_scene_group=report['group'])
    return result, t, ids


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--continuous-run', type=Path, required=True)
    p.add_argument('--preset-run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    assert not a.target.exists(), 'Preserve previous reference definitions'
    current, _, _ = audit(a.continuous_run)
    reference, t, ids = audit(a.preset_run)
    j = int(ids[0])-1
    wrist, obj = t['wrist'][j], t['object'][j]
    inv = Rotation.from_quat(wrist[3:]).inv()
    relative = np.r_[inv.apply(obj[:3]-wrist[:3]),
                     (inv*Rotation.from_quat(obj[3:])).as_quat()]
    physics = json.loads((a.preset_run/'physics.json').read_text())
    motor_ids = physics['hand_indices']
    assert np.allclose(t['q'][j], t['all_dof_position'][j,motor_ids], rtol=0, atol=1e-7)
    target = dict(kind='finger_surface_operation_reference_v1',status='previous preset operation validated; continuous acquisition UNPROVEN',
        reference_image_interpretation='Knife handle across the volar surfaces of non-thumb digits; thumb on slider face. Image alone does not establish forces, hidden contacts, exact pose or joint angles.',
        desired_contact_roles=dict(thumb='slider-facing surface, with width clearance and full stroke reach',
            non_thumb='distributed support on handle underside across finger pads; four preferred, do not require every finger touching every frame',
            finger_posture='Prefer a coherent volar support surface with modest flexion, closer to the reference image; existing preset remains visibly more flexed and is not an exact image match',
            clearance='slider swept region and future blade work region kept clear'),
        selection='One existing operation-validated preset endpoint closer to desired topology; not an arbitrary cache nearest-neighbor',
        source_run=str(a.preset_run),source_trace_sha256=reference['source_trace_sha256'],frame=j,
        quaternion_order='xyzw',pose_convention='T_hand_object = inverse(T_world_hand) @ T_world_object',
        hand_joint_names=[physics['robot_dof_names'][i] for i in motor_ids],
        measured_hand_q_rad=t['q'][j].tolist(),
        nominal_hand_motor_targets_rad=t['reference_targets'][j,motor_ids].tolist(),
        actual_hand_motor_targets_rad=t['targets'][j,motor_ids].tolist(),
        object_in_hand_xyzw=relative.tolist(),slider_actual_joint_m=float(t['slider'][j]),
        source_world_wrist_xyzw=wrist.tolist(),source_world_object_xyzw=obj.tolist(),
        contact_summary=reference['contacts'],operation_evidence={k:reference[k] for k in ['endpoint_max_errors_m','world_drift_max_m','world_rotation_max_rad','basic_10mm','strict_2mm','stable_world_10mm_025rad']},
        use_restriction='Planning/evidence reference only. Never load into an ongoing continuous tabletop run. Reaching this target by real manipulation remains unverified.',
        physical_limitations='Original hand gravity OFF, existing G2 servo/collision filters, uncalibrated friction/free slider; not hardware validation',
        no_new_training_or_physics_execution=True)
    a.target.parent.mkdir(parents=True, exist_ok=True)
    a.target.write_text(json.dumps(target,ensure_ascii=False,indent=2)+'\n')
    result = dict(scope='Read-only comparison of two real recorded operation windows; no new simulation or training',
        continuous=current,preset_reference=reference,target_file=str(a.target),
        caveat='Contact fraction and bottom-surface geometry do not measure load. Preset success is not table acquisition success.')
    (a.output/'contact-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), constrained_layout=True)
    x = np.arange(5)
    for offset, source, name in [(-.18,current,'Current continuous success'),(.18,reference,'Existing preset target (A)')]:
        axes[0].bar(x+offset,[source['contacts'][f]['operation_contact_fraction'] for f in DIGITS],.36,label=name)
    axes[0].set_xticks(x);axes[0].set_xticklabels(DIGITS);axes[0].set_ylim(0,1.15)
    axes[0].set_title('Actual pad contact over20s');axes[0].set_ylabel('Fraction of control frames');axes[0].legend(fontsize=8)
    for ax,source,title in zip(axes[1:],[current,reference],['Current continuous grasp','Operation-validated preset target']):
        ax.add_patch(plt.Rectangle((-73.5,-9.5),147,19,facecolor='#dddddd',edgecolor='black'))
        for i,f in enumerate(DIGITS[1:]):
            point=source['contacts'][f]['point_median_m']
            if point is None:continue
            ax.scatter(point[2]*1000,point[0]*1000,s=75,color=plt.cm.tab10(i+1));ax.annotate(f,(point[2]*1000,point[0]*1000),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
        ax.set(xlim=(-80,80),ylim=(-15,22),xlabel='Handle length z (mm)',ylabel='Handle width x (mm)',title=title)
        ax.set_aspect('equal')
    fig.suptitle('Reference-image grasp assessment: contact topology, not support-force measurement')
    fig.savefig(a.output/'contact-topology-comparison.png',dpi=160);plt.close(fig)
    print(json.dumps({label:dict(fractions={f:row['contacts'][f]['operation_contact_fraction'] for f in DIGITS},
        four_pad_fraction=row['four_non_thumb_bottom_pad_fraction'],three_pad_fraction=row['three_or_more_non_thumb_bottom_pad_fraction'])
        for label,row in [('continuous',current),('preset',reference)]}))


if __name__ == '__main__':
    main()
