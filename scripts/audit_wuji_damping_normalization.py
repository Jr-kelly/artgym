"""Read frozen checkpoint statistics and run its actual observation normalizer.

This explains the representation of damping in the existing teacher. It neither
changes the checkpoint nor establishes that all resistance failures are caused
by normalization. The separately saved factorial physics probe provides the
behavioral intervention evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from rl_games.algos_torch.running_mean_std import RunningMeanStd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    saved = torch.load(args.checkpoint, map_location='cpu')
    state = saved[0] if 0 in saved else saved
    model = state['model']
    prefix = 'running_mean_std.'
    norm = RunningMeanStd((137,))
    norm.load_state_dict({k[len(prefix):]:v for k,v in model.items() if k.startswith(prefix)})
    norm.eval()
    # Policy111; privileged: object pose7, slider pose7, masses2, friction1.
    index = 111+7+7+2+1
    assert index == 128
    damping = torch.tensor([.3, 3., 30., 100., 300.])
    observations = norm.running_mean.float().expand(5, -1).clone()
    observations[:, index] = damping
    before = {k:v.clone() for k,v in norm.state_dict().items()}
    with torch.no_grad():
        normalized = norm(observations)[:, index]
    assert all(torch.equal(v, norm.state_dict()[k]) for k,v in before.items())
    mean = float(norm.running_mean[index])
    var = float(norm.running_var[index])
    raw = (damping-mean)/(var+norm.epsilon)**.5
    result = dict(status='completed', scope=__doc__, checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                  damping_observation_index=index, mean=mean, variance=var, epsilon=norm.epsilon,
                  rows=[dict(damping_Ns_per_m=float(d), before_clip=float(z), actual_normalized_input=float(n))
                        for d,z,n in zip(damping,raw,normalized)],
                  normalizer_unchanged=True,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  normalizer_source_sha256=hashlib.sha256(Path('rl_games/rl_games/algos_torch/running_mean_std.py').read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
