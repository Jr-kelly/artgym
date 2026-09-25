"""Explicit migration entry point: PPO on frozen student latents, privileged critic."""
from pathlib import Path
import hydra
from scripts import wuji_goal_common  # Isaac Gym before torch.
from isaacgymenvs.tasks.wuji_fixed_student_actor import register_task
from isaacgymenvs.learning.wuji_fixed_student_actor import register_models


def register():
    register_task()
    register_models()
    from isaacgymenvs.tasks.wuji_controller_student_actor import register_task as register_controller_task
    from isaacgymenvs.learning.wuji_controller_student_actor import register_models as register_controller_models
    register_controller_task()
    register_controller_models()


def main():
    register()
    from isaacgymenvs.train import launch_rlg_hydra
    # The upstream decorator uses a relative config path that only resolves
    # when train.py itself is the entry module. Resolve it explicitly here.
    config_dir = Path(__file__).resolve().parents[1] / 'isaacgymenvs/cfg'
    hydra.main(version_base='1.1', config_name='config', config_path=str(config_dir))(
        launch_rlg_hydra.__wrapped__)()


if __name__ == '__main__':
    main()
