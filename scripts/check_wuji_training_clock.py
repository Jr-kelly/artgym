"""Exercise the training clock in actual PhysX, then inherited evaluation.

This is a scheduling regression check, not a manipulation success evaluation.
The saved teacher supplies all twenty joint actions.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from omegaconf import OmegaConf
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arrival-control", action="store_true")
    parser.add_argument("--hold-bonus", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    task = "wuji_acquisition_official_arrival_control" if args.arrival_control else "wuji_acquisition_official_timed2"
    if args.hold_bonus:
        if args.arrival_control:
            raise ValueError("The endpoint bonus check uses fixed-time commands")
        task = "wuji_acquisition_official_timed_hold"
    cfg = configuration(task, 32,
        ["object=knife_wuji_precision_near01", "hand=wuji_paper_official_actuator", "test=False"],
        train="wujiAcquisitionSAPG", seed=20261009)
    (args.output / "config.yaml").write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, args.checkpoint)
    counts = dict(training_transitions=0, clock_switches=0, arrivals_held=0,
                  evaluation_arrivals=0, evaluation_off_clock_switches=0)
    if args.hold_bonus:
        counts["training_steps_with_positive_hold_bonus"] = 0
    original = env.compute_reward

    def check(actions):
        goal_before = env.goal_obj_dof_pos.clone()
        progress = env.progress_buf.clone()
        index_before = env.goal_indices.clone()
        original(actions)
        changed = (env.goal_obj_dof_pos != goal_before).any(dim=-1)
        arrival = env.goal_achieved_step.bool()
        if not env.eval_mode and not args.arrival_control:
            due = (progress > 0) & (progress % 60 == 0) & (env.reset_buf == 0)
            assert torch.equal(changed, due), "Training goals did not follow the clock"
            assert torch.equal(env.goal_indices[due], (index_before[due] + 1) % 2)
            off_clock = arrival & ~due
            assert not changed[off_clock].any(), "Arrival changed a timed training goal"
            assert env.training_goal_success_counted[off_clock].all(), "Success latch reset too early"
            counts["training_transitions"] += env.num_envs
            counts["clock_switches"] += int(due.sum())
            counts["arrivals_held"] += int(off_clock.sum())
        elif env.eval_mode:
            assert torch.equal(changed, arrival), "Inherited evaluation switching changed"
            counts["evaluation_arrivals"] += int(arrival.sum())
            counts["evaluation_off_clock_switches"] += int((changed & (progress % 60 != 0)).sum())
        else:
            assert torch.equal(changed, arrival), "Arrival control did not switch on success"
            counts["training_transitions"] += env.num_envs
            counts["arrivals_held"] += int(arrival.sum())
            counts["clock_switches"] += int((changed & (progress % 60 != 0)).sum())
        assert torch.isfinite(env.rew_buf).all()
        if args.hold_bonus and not env.eval_mode:
            bonus = float(env.extras["EndpointHoldReward"])
            assert 0 <= bonus <= 1
            counts["training_steps_with_positive_hold_bonus"] += int(bonus > 0)

    env.compute_reward = check
    try:
        for mode in ["training", "evaluation"]:
            if mode == "evaluation":
                env.configure_grasp_consecutive_evaluation("000",
                    goal_sequence=tuple(cfg.object.task.goals), grasp_split="train", episodes_per_grasp=32)
            observations = player.env_reset(player.env)
            init_player_rnn_for_batch(player, env.num_envs)
            for _ in range(125):
                actions = player.get_action(observations, is_deterministic=True)
                observations, _, done, _ = player.env_step(player.env, actions)
                if player.is_rnn:
                    ids = done.nonzero(as_tuple=False).squeeze(-1)
                    for state in player.states:
                        state[:, ids, :] = 0
            print(json.dumps(dict(mode=mode, counts=counts)), flush=True)
        assert all(counts[key] > 0 for key in counts), "The check did not exercise all paths"
        result = dict(status="passed", counts=counts, arrival_control=args.arrival_control,
            endpoint_hold_reward=args.hold_bonus,
            checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
            sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
                Path(__file__), Path("isaacgymenvs/tasks/wuji_timed_acquisition.py")]},
            scope=__doc__)
        (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == "__main__":
    main()
