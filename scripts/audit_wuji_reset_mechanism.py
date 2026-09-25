"""Frozen reset diagnosis: input-normalizer swaps or constant initial-target holding.

These are explicitly labelled counterfactual controllers, not trained checkpoints
or deployment candidates. All other timed evaluation physics and scoring remain
the same. No checkpoint file is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import audit_wuji_timed_commands as base  # IsaacGym before torch.
import torch


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--normalizer-source', type=Path)
    parser.add_argument('--constant-initial-targets', action='store_true')
    options, remaining = parser.parse_known_args()
    output = Path(remaining[remaining.index('--output')+1])
    checkpoint = Path(remaining[remaining.index('--checkpoint')+1])
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'intervention.json').exists()
    make_player = base.make_player
    finalize = None
    record = dict(scope=__doc__, checkpoint_sha256=digest(checkpoint),
                  normalizer_source_sha256=digest(options.normalizer_source) if options.normalizer_source else None,
                  constant_initial_targets=options.constant_initial_targets,
                  source_sha256=digest(Path(__file__)), transitions=0)

    def wrapped(cfg, path):
        nonlocal finalize
        env, player = make_player(cfg, path)
        model = player.model
        original = {k: v.clone() for k, v in model.state_dict().items()}
        normalizer_keys = ['running_mean_std.running_mean', 'running_mean_std.running_var', 'running_mean_std.count']
        expected = {k: v.clone() for k, v in original.items()}
        if options.normalizer_source:
            source = torch.load(options.normalizer_source, map_location=player.device)
            source = source[0] if 0 in source else source
            for key in normalizer_keys:
                value = source['model'][key]
                assert value.shape == original[key].shape and value.dtype == original[key].dtype
                assert torch.isfinite(value).all()
                expected[key] = value
            assert (expected['running_mean_std.running_var'] > 0).all()
            model.load_state_dict(expected, strict=True)
        assert all(torch.equal(model.state_dict()[k], v) for k, v in expected.items())
        assert all(torch.equal(model.state_dict()[k], v) for k, v in original.items() if k not in normalizer_keys)
        model.eval()
        record['input_normalizer_only'] = True
        record['changed_normalizer_tensors'] = [k for k in normalizer_keys if not torch.equal(expected[k], original[k])]
        pre = env.pre_physics_step

        def step(action):
            pre(torch.zeros_like(action) if options.constant_initial_targets else action)
            if options.constant_initial_targets:
                # The normal controller's FP32 scale/unscale path is retained.
                error = (env.cur_targets[:, :20]-env.init_targets[:, :20]).abs().max()
                assert error < 2e-6, float(error)
                assert torch.count_nonzero(env.actions) == 0
                record['maximum_constant_target_error_rad'] = max(
                    record.get('maximum_constant_target_error_rad', 0.), float(error))
            record['transitions'] += env.num_envs

        env.pre_physics_step = step
        def finish():
            assert all(torch.equal(model.state_dict()[k], v) for k, v in expected.items()), 'Frozen tensors changed'
            assert not model.training and not model.running_mean_std.training
            record['frozen_tensors_verified_after_physics'] = True
            (output/'intervention.json').write_text(json.dumps(record, indent=2)+'\n')
        # The pinned original timed evaluator has no cleanup callback. Verify
        # the separately owned model tensors after it returns normally; never
        # access freed PhysX state here or depend on a newer evaluator hook.
        finalize = finish
        return env, player

    base.make_player = wrapped
    sys.argv = [sys.argv[0]]+remaining
    (output/'source_intervention.py').write_bytes(Path(__file__).read_bytes())
    try:
        base.main()
        assert finalize is not None
        finalize()
        assert (output/'intervention.json').exists()
    finally:
        base.make_player = make_player


if __name__ == '__main__':
    main()
