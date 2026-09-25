"""Check copied TCN weights on real recorded causal inputs, without simulation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder
from scripts.wuji_command_slider import make_custom_command_base
from scripts.monitor_wuji_checkpoints import now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    torch.set_num_threads(2)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    source = args.root/'runs/wuji-goal/diagnostics/command-slider-2330-v3/fitting/provided-update0000.pth'
    original = torch.load(source, map_location='cpu')
    cpu, _ = make_encoder(original['encoder_spec'])
    cpu.load_state_dict(original['state_encoder'])
    cpu.eval()
    custom = make_custom_command_base(original).cuda().eval()
    manifest = json.loads((args.root/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data/manifest.json').read_text())
    results = []
    for item in manifest['sources']:
        p = args.root/'runs'/item['path'].split('/runs/', 1)[1]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
        with np.load(p) as z:
            x = z['history'][[0, 30, 75, 149]][:, [0, 29, 30, 59, 60, 89]].reshape(-1, 2055)
        with torch.no_grad():
            expected = cpu(torch.from_numpy(x))
            got = custom(torch.from_numpy(x).cuda()).cpu()
            repeated = custom(torch.from_numpy(x).cuda()).cpu()
        assert torch.equal(got, repeated)
        assert torch.allclose(expected, got, atol=2e-4, rtol=2e-5)
        difference = (expected-got).abs()
        results.append(dict(source=item['key'], dataset_sha256=item['sha256'], examples=len(x),
            output_max_difference=float(difference.max()),
            physical_max_difference_by_component=(difference*torch.tensor(original['output_scales'])).max(0).values.tolist(),
            repeated_gpu_output_exact=True))
    result = dict(created=now(), status='passed', no_physics=True, no_training=True, rows=results,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        weights_copied_exact=True, artifact_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        scope='96 recorded teacher/student fast/slow causal history inputs. CPU original versus GPU custom arithmetic agrees within declared tolerance; no bitwise legacy or task-success claim.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
