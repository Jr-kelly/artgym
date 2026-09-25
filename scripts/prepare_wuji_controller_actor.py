"""Add exactly zero controller residual weights to a frozen actor checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    expected = 'a2d68ba64d0c34fe04fd1ffa408235f0056f2717d779cef70155ef8b37f37b5a'
    assert hashlib.sha256(args.source.read_bytes()).hexdigest() == expected
    payload = torch.load(args.source, map_location='cpu')
    actor = payload[0] if 0 in payload else payload
    model = actor['model']
    before = {name: value.clone() for name, value in model.items()}
    weight, bias = 'a2c_network.controller_adapter.weight', 'a2c_network.controller_adapter.bias'
    assert weight not in model and bias not in model
    model[weight] = torch.zeros(16, 20, dtype=model['a2c_network.mu.weight'].dtype)
    model[bias] = torch.zeros(16, dtype=model['a2c_network.mu.weight'].dtype)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, args.output)
    saved = torch.load(args.output, map_location='cpu')
    saved = saved[0] if 0 in saved else saved
    assert set(saved['model']) == set(before) | {weight, bias}
    assert all(torch.equal(value, saved['model'][name]) for name, value in before.items())
    assert saved['model'][weight].count_nonzero() == saved['model'][bias].count_nonzero() == 0
    record = dict(source=str(args.source), source_sha256=expected,
        artifact=str(args.output), sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        added_tensors={weight:[16,20],bias:[16]}, all_original_model_tensors_exact=True,
        note='Initialization only; optimizer state is inherited but must be discarded by checkpoint_weights_only=True before PPO. Real CP0 behavior checked separately.')
    args.output.with_name('manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
