"""Create or verify the sigma-only initialization used by the Wuji PPO ablation."""
import argparse
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import torch


def transformed(source):
    original = torch.load(source, map_location='cpu')
    result = copy.deepcopy(original)
    before, after = original.get(0, original)['model'], result.get(0, result)['model']
    assert tuple(after['a2c_network.sigma'].shape) == (5, 20)
    after['a2c_network.sigma'].add_(math.log(.25))
    assert [name for name in after if not torch.equal(before[name], after[name])] == ['a2c_network.sigma']
    assert torch.allclose(after['a2c_network.sigma'].exp(), .25*before['a2c_network.sigma'].exp(), rtol=1e-6, atol=1e-8)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--verify-existing', action='store_true')
    args = parser.parse_args()
    result = transformed(args.source)
    if args.verify_existing:
        stored = torch.load(args.artifact, map_location='cpu')
        expected, actual = result.get(0, result)['model'], stored.get(0, stored)['model']
        assert set(actual) == set(expected)
        assert all(torch.equal(actual[name], value) for name, value in expected.items())
    else:
        assert not args.artifact.exists()
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        torch.save(result, args.artifact)
    print(json.dumps(dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                          artifact_sha256=hashlib.sha256(args.artifact.read_bytes()).hexdigest(),
                          preparation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                          only_changed_model_key='a2c_network.sigma', sigma_factor=.25,
                          existing_artifact_verified=args.verify_existing)))


if __name__ == '__main__':
    main()
