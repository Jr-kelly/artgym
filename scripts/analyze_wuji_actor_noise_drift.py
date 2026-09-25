"""Inspect saved noise parameters and training curves without rerunning physics."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    results = []
    names = ['wuji_student_actorrl_replaycp25_sigmaquarter_broad0_seed62_v1',
             'wuji_student_actorrl_smallcp25_pose1_noramp_seed64_v1']
    for name in names:
        run = args.root/'runs'/name
        checkpoints = []
        first = None
        for epoch in [1, 25, 50, 100]:
            path = run/'checkpoints'/('epoch_%06d.pth' % epoch)
            if not path.exists():
                path = run/'evaluation/inbox'/path.name
            payload = torch.load(path, map_location='cpu')
            if 0 in payload:
                payload = payload[0]
            sigma = payload['model']['a2c_network.sigma'].exp().clone()
            assert sigma.shape == (5, 20) and torch.isfinite(sigma).all()
            if first is None:
                first = sigma.clone()
            checkpoints.append(dict(epoch=epoch, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                standard_deviations=sigma.tolist(), mean_by_group=sigma.mean(1).tolist(),
                thumb_mean_by_group=sigma[:, 16:].mean(1).tolist(),
                minimum_ratio_to_cp1=float((sigma/first).min()), maximum_ratio_to_cp1=float((sigma/first).max())))
            del payload
        accumulator = EventAccumulator(str(run/'summaries'))
        accumulator.Reload()
        curves = {}
        for tag in accumulator.Tags()['scalars']:
            if (tag.endswith('/iter') or tag in ['losses/entropy', 'episode_cumulative/counted_successes']):
                curves[tag] = [dict(step=r.step, value=r.value) for r in accumulator.Scalars(tag)]
        results.append(dict(run=name, checkpoints=checkpoints, curves=curves))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(runs=results, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        caveats='Saved Gaussian std is coefficient-conditioned and frozen within state, not all action variability. Deterministic audit uses means; sigma affects training data distribution. TensorBoard reward components are logger samples, not a frozen-policy matched return comparison.')
    args.output.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps([dict(run=r['run'], final_min_ratio=r['checkpoints'][-1]['minimum_ratio_to_cp1'],
        final_max_ratio=r['checkpoints'][-1]['maximum_ratio_to_cp1']) for r in results]))


if __name__ == '__main__':
    main()
