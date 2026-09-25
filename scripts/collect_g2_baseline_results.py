"""Publish fixed A/B/C cases separately from heterogeneous development trials."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone

PRIMARY={
    'A':'A-g2-integral-v12',
    'B':'B-pinch8-teacher-grasp0-v15',
    'C':'C-pinch8-student-ideal-grasp0-v21',
}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('runs/g2-tabletop-v1'));a=p.parse_args()
    primary={}
    for group,name in PRIMARY.items():
        report=json.loads((a.root/name/'report.json').read_text())
        primary[group]=dict(trial=name,samples=1,pickup_successes=None if group=='A' else int(report['grasp_success']),
            pickup_attempts=None if group=='A' else 1,conditional_operation_attempts=1,
            conditional_operation_successes=int(report['whole_success']),whole_successes=int(report['whole_success']),
            continuous_operation_s=report['operation_steps']/30,
            slider_travel_mm=report['slider_travel_m']*1000,
            endpoint_errors_mm=[e['max_error_m']*1000 for e in report['endpoints']],
            endpoints_10mm=report['basic_10mm'],endpoints_2mm=report['strict_2mm'],
            world_drift_mm=report['world_drift_max_m']*1000,world_rotation_rad=report['world_rotation_max_rad'],
            hand_drift_mm=report['hand_relative_drift_max_m']*1000,no_drop=report['natural_no_drop'],
            stable_10mm_025rad=report['stable_world_10mm_025rad'],
            student_initialization='ideal simulation truth; not deployable' if group=='C' else None,
            teacher_sha256=report['teacher_sha256'],student_sha256=report.get('student_sha256'))
    development=[]
    for proc in sorted(a.root.glob('*-process.json')):
        name=proc.name[:-len('-process.json')]
        path=a.root/name
        if (path/'failure.json').exists():
            failure=json.loads((path/'failure.json').read_text())
            row=dict(trial=name,status='aborted',phase=failure.get('last_phase'),reason=failure.get('message'))
        elif (path/'report.json').exists():
            report=json.loads((path/'report.json').read_text())
            row=dict(trial=name,status='completed' if 'group' in report else 'diagnostic_completed',group=report.get('group'),pickup_success=report.get('grasp_success'),
                operation_steps=report.get('operation_steps'),whole_success=report.get('whole_success'),
                reason=report.get('failure_class') or report.get('acquisition_stage_failure'))
            if row['reason'] is None and not report.get('natural_no_drop',True):row['reason']='operation_drop'
        else:
            info=json.loads(proc.read_text());pid=info['pid'];stat=Path('/proc',str(pid),'stat')
            alive=stat.exists() and stat.read_text().split(') ')[1][0]!='Z'
            row=dict(trial=name,status='running' if alive else 'preflight_or_initialization_failure',
                reason=None if alive else 'Inspect retained log/plan; not counted as physical pickup failure')
        development.append(row)
    out=dict(created=datetime.now(timezone.utc).isoformat(),primary_cases=primary,development=development,
        interpretation='Each primary group is one fixed development case, not a generalization estimate. Heterogeneous attempts are not pooled into a success rate.',
        small_variation_validation='Not started: fixed continuous B/C pipeline has not succeeded.')
    (a.root/'abc-baseline-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(primary,indent=2))

if __name__=='__main__':main()
