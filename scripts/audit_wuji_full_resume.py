"""Check committed checkpoints and optimizer counters after a declared full resume."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import torch


def state(path):
    value = torch.load(path, map_location="cpu")
    return value[0] if 0 in value else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=float, default=0.)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = [root/("runs/wuji_acq_official_actuator_support%dmrad_resume25_v2/checkpoints/epoch_000050.pth" % span)
             for span in [40, 200]]
    deadline = time.monotonic()+args.wait_seconds
    while not all(p.exists() for p in paths):
        if time.monotonic() >= deadline:
            raise RuntimeError("The declared CP50 files did not appear within the wait budget")
        print(json.dumps(dict(status="waiting_for_committed_cp50", missing=[str(p) for p in paths if not p.exists()])), flush=True)
        time.sleep(min(30., max(0., deadline-time.monotonic())))
    records = []
    for span, checkpoint in zip([40, 200], paths):
        source = root/("runs/wuji_acq_official_actuator_support%dmrad_v1/checkpoints/epoch_000025.pth" % span)
        pipeline = json.loads((checkpoint.parent.parent/"pipeline-status.json").read_text())
        command = next(s["command"] for s in pipeline["stages"] if s["name"] == "teacher")
        assert "+train.params.config.checkpoint_weights_only=False" in command
        assert "checkpoint="+str(source) in command
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        assert source_hash == pipeline["spec"]["source_checkpoint_sha256"]
        before, after = state(source), state(checkpoint)
        assert (before["epoch"], before["frame"], before["num_actors"], before["world_size"]) == (25, 4096000, 5120, 1)
        assert (after["epoch"], after["frame"], after["num_actors"], after["world_size"]) == (50, 8192000, 5120, 1)
        bopt, aopt = before["optimizer"]["state"], after["optimizer"]["state"]
        assert bopt.keys() == aopt.keys() and len(aopt) > 0
        steps = []
        for key in bopt:
            assert float(bopt[key]["step"]) == 600
            assert float(aopt[key]["step"]) == 1200, "Adam steps indicate reset or a changed update schedule"
            for moment in ["exp_avg", "exp_avg_sq"]:
                assert bopt[key][moment].shape == aopt[key][moment].shape
                assert torch.isfinite(aopt[key][moment]).all()
            steps.append(float(aopt[key]["step"]))
        assert before["model"].keys() == after["model"].keys()
        changed = []
        normalization = {}
        for key, value in after["model"].items():
            assert value.shape == before["model"][key].shape
            assert torch.isfinite(value).all()
            if not torch.equal(value, before["model"][key]):
                changed.append(key)
            if "running" in key and "count" in key:
                assert (value >= before["model"][key]).all()
                normalization[key] = dict(before=before["model"][key].tolist(), after=value.tolist())
        assert changed and normalization
        records.append(dict(span_mrad=span, source_sha256=source_hash,
            resumed_checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            epoch=after["epoch"], frame=after["frame"], optimizer_states=len(aopt),
            optimizer_step_min=min(steps), optimizer_step_max=max(steps),
            changed_model_tensors=len(changed), normalization_counts=normalization,
            formal_command=command, scope="Evidence of full counters and Adam continuation; physics/RNN reset by design. "
                "Does not assert trajectory identity with uninterrupted training or recovery of the exact first resumed parameter tensor."))
    result = dict(status="verified", records=records,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        restore_source_sha256=hashlib.sha256((root/"rl_games/rl_games/algos_torch/a2c_continuous.py").read_bytes()).hexdigest())
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(dict(status="verified", optimizer_steps=[r["optimizer_step_max"] for r in records])))


if __name__ == "__main__":
    main()
