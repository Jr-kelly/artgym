"""Independently recompute held-out sensor errors and optimizer/data provenance."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common  # IsaacGym before torch.
import numpy as np
import torch
from scripts.wuji_rgb_state_model import RGBStateModel, OUTPUT_SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--device', default='cuda:0')
    args = p.parse_args()
    assert not args.output.exists()
    torch.set_num_threads(4)
    status = json.loads((args.run/'fitting/status.json').read_text())
    assert status['status'] == 'completed' and status['updates_completed'] == 5000
    models, before, results = {}, {}, {}
    initials = []
    for arm in ['rgb', 'masked']:
        cp = args.run/'fitting'/f'{arm}-update5000.pth'
        meta = json.loads(cp.with_suffix('.json').read_text())
        sha = hashlib.sha256(cp.read_bytes()).hexdigest()
        assert sha == meta['sha256']
        artifact = torch.load(cp, map_location='cpu')
        initial = torch.load(args.run/'fitting'/f'{arm}-update0000.pth', map_location='cpu')
        initials.append(tensor_digest(initial['state_dict']))
        assert artifact['update'] == 5000 and artifact['arm'] == arm
        steps = [int(v['step']) for v in artifact['optimizer']['state'].values()]
        assert set(steps) == {5000}
        model = RGBStateModel(artifact['feature_mean'], artifact['feature_scale'])
        model.load_state_dict(artifact['state_dict']); model.to(args.device).eval()
        before[arm] = tensor_digest(model.state_dict())
        assert before[arm] != initials[-1]
        assert np.array_equal(artifact['feature_mean'], initial['feature_mean'])
        assert np.array_equal(artifact['feature_scale'], initial['feature_scale'])
        models[arm] = model
        results[arm] = dict(sha256=sha, optimizer_steps=steps, squared=np.zeros(7), maximum=np.zeros(7))
    assert initials[0] == initials[1] == status['initial_tensor_sha256']
    ntrain = nval = chunks = 0
    sum_x = np.zeros(96); sum_x2 = np.zeros(96)
    for source in status['data_spec']['collections']:
        folder = args.root/source['path']
        statepath = folder/'collection-status.json'
        assert hashlib.sha256(statepath.read_bytes()).hexdigest() == source['status_sha256']
        collection = json.loads(statepath.read_text())
        selected = np.array(collection['selected_initial_rows'])
        training = selected % 100 < 20
        assert set(selected[training]).isdisjoint(selected[~training])
        for row in collection['chunks']:
            path = folder/row['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
            with np.load(path) as z:
                x = np.concatenate([z['known_initial'], z['proprio'], z['goal']], -1)
                tx = x[:, training].reshape(-1, 96).astype(np.float64)
                ntrain += len(tx); sum_x += tx.sum(0); sum_x2 += (tx*tx).sum(0)
                vx = x[:, ~training].reshape(-1, 96)
                vy = z['target'][:, ~training, :7].reshape(-1, 7)
                images = z['rgb'][:, ~training].reshape(-1, 320, 320, 3)
                assert z['active'].all()
                nval += len(vx)
                for start in range(0, len(vx), 128):
                    im = torch.tensor(images[start:start+128], device=args.device).permute(0, 3, 1, 2).float()/255.-.5
                    features = torch.tensor(vx[start:start+128], device=args.device)
                    for arm, model in models.items():
                        with torch.no_grad():
                            prediction = model(im, features, mask_image=arm == 'masked')
                            error = prediction.cpu().numpy()*np.array(OUTPUT_SCALES)-vy[start:start+128]
                        results[arm]['squared'] += (error*error).sum(0)
                        results[arm]['maximum'] = np.maximum(results[arm]['maximum'], np.abs(error).max(0))
            chunks += 1
    assert (ntrain, nval) == (24000, 12000)
    mean = (sum_x/ntrain).astype(np.float32)
    scale = np.maximum(np.sqrt(np.maximum(sum_x2/ntrain-(sum_x/ntrain)**2, 0)), .01).astype(np.float32)
    for arm, model in models.items():
        assert np.allclose(mean, model.feature_mean.cpu().numpy(), atol=2e-7, rtol=1e-6)
        assert np.allclose(scale, model.feature_scale.cpu().numpy(), atol=2e-7, rtol=1e-6)
        assert tensor_digest(model.state_dict()) == before[arm]
        result = results[arm]
        result['rmse'] = np.sqrt(result.pop('squared')/nval).tolist()
        result['max_absolute_error'] = result.pop('maximum').tolist()
        reported = status['validation'][-1]['arms'][arm]
        assert np.allclose(result['rmse'], reported['rmse'], atol=1e-7, rtol=.002)
        assert np.allclose(result['max_absolute_error'], reported['max_absolute_error'], atol=1e-6, rtol=.002)
    atomic_json(args.output, dict(status='passed',finished=now(),arms=results,training_samples=ntrain,
        validation_samples=nval,source_chunks_verified=chunks,normalization_training_only=True,
        matching_initial_weights=True,models_unchanged=True,physics_transitions=0,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Held-out old initial rows; offline errors only, no task or hardware success.'))
    print(args.output)


if __name__ == '__main__':
    main()
