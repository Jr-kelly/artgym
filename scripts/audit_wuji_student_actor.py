"""Fixed-clock evaluation of PPO adapted actors driven by frozen student latents."""
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
from scripts.train_wuji_student_actor import register
from scripts.check_wuji_student_actor_runtime import overrides, STUDENT, STUDENT_SHA


def main():
    register()
    original = wuji_goal_common.configuration

    def configuration(task, envs, requested=(), train=None, seed=1616):
        assert task == 'wuji_fixed_student_actor'
        return original(task, envs, list(requested)+overrides(), train='wujiFixedStudentActorSAPG', seed=seed)

    wuji_goal_common.configuration = configuration
    from scripts import audit_wuji_timed_commands
    # This entry point is a student control policy even though it loads a
    # full PPO checkpoint. The parent artifact loader is intentionally unused.
    assert '--student-artifact' not in sys.argv
    try:
        audit_wuji_timed_commands.main()
    finally:
        wuji_goal_common.configuration = original
        audit_wuji_timed_commands.configuration = original
    out = Path(sys.argv[sys.argv.index('--output')+1])
    report_path = out/'report.json'
    report = json.loads(report_path.read_text())
    (out/'base_report.json').write_bytes(report_path.read_bytes())
    report.update(policy_kind='learned_student_with_ppo_actor_adaptation', fixed_student_artifact=STUDENT,
                  fixed_student_sha256=STUDENT_SHA, actor_current_privileged_object_inputs=False,
                  critic_current_privileged_object_inputs=True,
                  scope='PPO actor consumes111 deployable policy inputs, frozen16dim student latent and SAPG ID; encoder consumes50frames of measuredjointangles and historicalactions plusinitial55. Currentobject21 andcontact5 are critic-only. Existing development initial states unless explicitly regenerated. No hardware claim.')
    root = Path(__file__).resolve().parents[1]
    files = ['scripts/audit_wuji_student_actor.py', 'scripts/check_wuji_student_actor_runtime.py',
             'isaacgymenvs/learning/wuji_fixed_student_actor.py', 'isaacgymenvs/tasks/wuji_fixed_student_actor.py']
    report['student_actor_sources'] = {}
    for name in files:
        data = (root/name).read_bytes()
        report['student_actor_sources'][name] = hashlib.sha256(data).hexdigest()
        (out/('student-actor-'+Path(name).name)).write_bytes(data)
    report_path.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
