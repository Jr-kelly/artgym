"""Strict fixed-clock audit for controller-residual and masked-input actors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
from scripts.train_wuji_student_actor import register
from scripts.check_wuji_student_actor_runtime import overrides, STUDENT, STUDENT_SHA


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--controller-enabled',choices=['true','false'],required=True)
    args,remaining=parser.parse_known_args()
    sys.argv=[sys.argv[0]]+remaining
    register()
    original=wuji_goal_common.configuration

    def configuration(task,envs,requested=(),train=None,seed=1616):
        assert task=='wuji_controller_student_actor'
        additions=overrides()+['train.params.network.controller_adapter.enabled='+args.controller_enabled]
        return original(task,envs,list(requested)+additions,train='wujiControllerStudentSAPG',seed=seed)

    wuji_goal_common.configuration=configuration
    from scripts import audit_wuji_timed_commands
    try:
        audit_wuji_timed_commands.main()
    finally:
        wuji_goal_common.configuration=original
        audit_wuji_timed_commands.configuration=original
    output=Path(sys.argv[sys.argv.index('--output')+1])
    path=output/'report.json'
    report=json.loads(path.read_text())
    report.update(policy_kind='learned_student_with_controller_residual',controller_enabled=args.controller_enabled=='true',
        fixed_student_artifact=STUDENT,fixed_student_sha256=STUDENT_SHA,
        actor_current_privileged_object_inputs=False,critic_current_privileged_object_inputs=True,
        controller_inputs='20 current issued joint targets minus measured joint angles, divided by.1rad and clipped[-5,5]; masked to0 in control arm. No force/object truth.',
        scope='Frozen student with learned actor/critic and linear20to16 residual; same strict development scorer, no hardware claim.')
    root=Path(__file__).resolve().parents[1]
    files=['scripts/audit_wuji_controller_actor.py','isaacgymenvs/tasks/wuji_controller_student_actor.py',
           'isaacgymenvs/learning/wuji_controller_student_actor.py']
    report['controller_sources']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
    for name in files:
        (output/('controller-'+Path(name).name)).write_bytes((root/name).read_bytes())
    path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
