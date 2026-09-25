"""Time the frozen command estimator without physics or parameter changes."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
from scripts import wuji_goal_common
import torch
from scripts.wuji_physical_state_encoder import make_encoder
from scripts.wuji_command_slider import CommandSliderEncoder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--custom-tcn', action='store_true')
    args = parser.parse_args()
    assert not args.output.exists()
    torch.set_num_threads(2)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    data = torch.load(args.artifact, map_location='cpu')
    base, _ = make_encoder(data['encoder_spec'])
    base.load_state_dict(data['state_encoder'])
    reference = None
    if args.custom_tcn:
        reference = base.eval()
        spec = copy.deepcopy(data['encoder_spec'])
        spec['temporal']['impl'] = 'custom_tcn'
        custom, _ = make_encoder(spec)
        mapped = {k.replace('.conv.', '.') if k.startswith('temporal_model.') else k: v
            for k, v in data['state_encoder'].items()}
        custom.load_state_dict(mapped)
        assert all(torch.equal(custom.state_dict()[k], v) for k, v in mapped.items())
        base = custom
    model = CommandSliderEncoder(base, data).to(args.device).eval()
    rows = []
    for count in [3, 332]:
        x = torch.zeros((count, 2055), device=args.device)
        # Valid known initial unit body and link quaternions.
        x[:, 2000+26] = 1
        x[:, 2000+33] = 1
        targets = torch.zeros((count, 20), device=args.device)
        difference = None
        if reference is not None:
            with torch.no_grad():
                expected = reference(x.cpu())
                got = model.base(x).cpu()
                difference = float((expected-got).abs().max())
                assert torch.allclose(expected, got, atol=2e-4, rtol=2e-5), difference
                print(json.dumps(dict(batch=count, cpu_original_vs_custom_max_difference=difference)), flush=True)
        for name, call in [('base_tcn', lambda: model.base(x)), ('full_estimator', lambda: model(x, targets))]:
            elapsed = []
            with torch.no_grad():
                for iteration in range(4):
                    if args.device == 'cuda':
                        torch.cuda.synchronize()
                    start = time.perf_counter()
                    prediction = call()
                    if args.device == 'cuda':
                        torch.cuda.synchronize()
                    elapsed.append(time.perf_counter()-start)
                    print(json.dumps(dict(batch=count, module=name, iteration=iteration, seconds=elapsed[-1])), flush=True)
            assert torch.isfinite(prediction).all()
            rows.append(dict(batch=count, module=name, seconds=elapsed,
                warm_mean_seconds=sum(elapsed[1:])/3,
                cpu_original_vs_custom_max_difference=difference))
    result = dict(rows=rows, no_physics=True, unchanged_parameters=True,
        device=args.device, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        custom_tcn=args.custom_tcn, weights_copied_exact=True,
        artifact_sha256=hashlib.sha256(args.artifact.read_bytes()).hexdigest(),
        scope='Synthetic inputs, four inference calls per condition; excludes actor and physics. Runs alongside evaluation, so wall time includes contention.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
