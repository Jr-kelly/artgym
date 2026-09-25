"""Check configured physical damping and actual privileged inputs before training."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--damping', type=float, choices=[.3, 3.], required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    obj = 'knife_wuji_precision_damping3' if args.damping == 3. else 'knife_wuji_precision_near01'
    cfg = configuration('wuji_acquisition_official_timed2', 32,
        ['object='+obj, 'hand=wuji_paper_official_actuator', 'test=False'],
        train='wujiAcquisitionSAPG', seed=20261016)
    assert cfg.object.default_props.dof_damping == args.damping
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, args.checkpoint)
    checks = dict(privileged_checks=0, clock_switches=0, transitions=0)
    original = env._compute_sapg_priv_observations

    def observations():
        policy, priv = original()
        assert torch.allclose(priv[:, 17], torch.full((32,), args.damping, device=env.device))
        checks['privileged_checks'] += 1
        return policy, priv

    env._compute_sapg_priv_observations = observations
    reward_base = env.compute_reward

    def reward(actions):
        goal = env.goal_obj_dof_pos.clone()
        progress = env.progress_buf.clone()
        reward_base(actions)
        due = (progress>0) & (progress%60==0) & (env.reset_buf==0)
        assert torch.equal((goal!=env.goal_obj_dof_pos).any(-1), due)
        checks['clock_switches'] += int(due.sum())

    env.compute_reward = reward
    try:
        obs = player.env_reset(player.env)
        init_player_rnn_for_batch(player, 32)
        for step in range(125):
            if step in [0, 124]:
                for i in range(32):
                    props = env.gym.get_actor_dof_properties(env.envs[i], env.object_handles[i])
                    assert np.isclose(props['damping'][0], args.damping)
            with torch.no_grad():
                action = player.get_action(obs, is_deterministic=True)
            obs, rew, done, _ = player.env_step(player.env, action)
            assert torch.isfinite(rew).all() and torch.isfinite(env.cur_targets).all()
            if player.is_rnn:
                ids = done.nonzero(as_tuple=False).squeeze(-1)
                for state in player.states:
                    state[:, ids, :] = 0
            checks['transitions'] += 32
        assert checks['clock_switches'] > 0 and checks['privileged_checks'] >= 125
        paths = [Path(__file__), Path('isaacgymenvs/tasks/wuji_timed_acquisition.py'),
                 Path('isaacgymenvs/tasks/artmanip.py'), Path('isaacgymenvs/cfg/object')/(obj+'.yaml')]
        result = dict(status='passed', damping=args.damping, object=obj, checks=checks, scope=__doc__,
                      checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                      sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
