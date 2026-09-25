"""Evaluate a frozen Sharpa teacher/student with an explicit repetition count."""
import json
from pathlib import Path
import sys


def main():
    student='--student-artifact' in sys.argv
    if student:
        from scripts.eval_sharpa_student_audited import main as evaluate
    else:
        from isaacgymenvs.eval_consecutive import main as evaluate
    evaluate()
    output=Path(sys.argv[sys.argv.index('--summary-output')+1])
    count=int(sys.argv[sys.argv.index('--episodes-per-grasp')+1])
    report=json.loads(output.read_text())
    assert report['episodes_per_grasp']==count
    report['frozen_reference_scope']=f'Frozen student finalCP1000 or its fixed teacherCP2100; five previously evaluated geometries, all valid grasps x{count} new randomized episodes. Original10mm consecutive-cycle criterion, not Wuji2mm timed commands or hardware.'
    if student:
        assert report['student_audit']['completed_updates']==1000
        report['student_audit']['scope']=report['frozen_reference_scope']
    output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
