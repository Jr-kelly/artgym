# Restore and reproduce the bounded experiment

All commands run at the repository root on the `feat/wuji-unified-policy-20260930` branch. They create new output directories; do not overwrite the archived runs. This is IsaacGym/PhysX simulation of the historical knife and trained reset neighborhoods, with privileged teacher observations. No source routing is used at inference.

## Restore

Download the assets from the independent `wuji-unified-policy-20260930-v1` Release. The final asset index and each archive receipt give SHA256 and byte size. Each archive also contains a per-file hash manifest. For example:

```bash
python3 -m scripts.restore_wuji_unified wuji-unified-assets-and-resets.tar.gz --output .
python3 -m scripts.restore_wuji_unified wuji-unified-experts.tar.gz --output .
python3 -m scripts.restore_wuji_unified wuji-unified-baseline-historical.tar.gz --output .
python3 -m scripts.restore_wuji_unified wuji-unified-train-t2.tar.gz --output .
python3 -m scripts.restore_wuji_unified wuji-unified-train-t5.tar.gz --output .
```

The restorer verifies every member and refuses to replace a different existing file. The selected unified checkpoint is `runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth`, SHA256 `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`. It is the best **failed** unified candidate; it did not pass G2. Do not deploy it as a validated controller.

The exact hand mesh/URDF, knife assets, all reset arrays and constructor seed states are in the assets-and-resets archive. Source code and resolved per-run YAML remain in Git and raw run archives. Existing historical Releases and the website were not replaced.

## Runtime

Observed runtime: Python 3.8, PyTorch 2.1.0+cu118 and the existing IsaacGym TacSL build. See `receipts/runtime-pip-freeze.txt`. IsaacGym and a compatible NVIDIA driver must already be installed; the release does not redistribute a complete system or driver. Runtime relocation was tested at `/tmp/wuji-unified-runtime`, including the editable IsaacGym path; a copied environment with stale `.egg-link`/`.pth` paths is not sufficient.

On the execution machine:

```bash
export PYTHONPATH="$PWD:$PWD/rl_games"
export LD_LIBRARY_PATH="/tmp/wuji-unified-runtime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TORCH_EXTENSIONS_DIR=/tmp/wuji-unified-torch-extensions
export PYTHONUNBUFFERED=1
WUJI_PYTHON=/tmp/wuji-unified-runtime/bin/python
```

Change `WUJI_PYTHON` and the library prefix together for another installed environment. Only use authorized idle GPUs. The wrapper sets `CUDA_VISIBLE_DEVICES`, bounds wall time, obtains a per-GPU lease and records utilization. Run no more than two GPUs at once. A lease does not authorize another host.

## Re-run frozen evaluation

This command repeats the already frozen final evaluation; it is not a fresh holdout for future tuning. All five models must use the same reset arrays, batch size and scoring. The five checkpoint paths and hashes are fixed in `final-freeze.json`.

```bash
"$WUJI_PYTHON" -m scripts.run_wuji_unified_job \
  --name replay-final-t2-job --gpu 0 --timeout 5500 -- PYTHON \
  -m scripts.evaluate_wuji_unified_gate --stage replay-final-t2 \
  --states research/unified-policy-20260930/data/final-all.npy --seconds 2 \
  --models \
  historical=runs/unified-policy-20260930/experts/historical.pth \
  source3=runs/unified-policy-20260930/experts/source3.pth \
  single_historical=runs/unified-policy-20260930/bc-single-historical/epoch_000100.pth \
  single_source3=runs/unified-policy-20260930/bc-single-source3/epoch_000100.pth \
  unified=runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth
```

Use GPU 1, `--seconds 5` and distinct names for the other protocol. Restore the single-expert archives before running all five models. The unchanged scorer requires 600 steps, externally scheduled targets, each stage's last nine samples within 2 mm, valid/alive throughout, drift below 10 mm and rotation below 0.25 radians throughout.

Independent rescore:

```bash
"$WUJI_PYTHON" -m scripts.summarize_wuji_unified \
  --directories runs/unified-policy-20260930/replay-final-t2 runs/unified-policy-20260930/replay-final-t5 \
  --output research/unified-policy-20260930/replay-final-analysis
```

## Re-run unified BC or restore the optimizer

The original historical initialization used 100 epochs, 800 full-episode updates, 96 training trajectories and 32 held-out trajectories per source/protocol. The eight files have equal update frequency. Each complete 600-step episode is processed as six 100-step recurrent segments, carrying detached state and applying the previous transition's done mask. Loss balances open/close and moving/arrival/holding phases. Expert raw mean and executed clipped actions are saved separately; the baseline loss is raw-mean MSE. Actor and its own privileged encoder train; critic, normalization and SAPG embedding remain fixed.

```bash
WUJI_DATA=()
for source in 0 1 2 3; do
  for seconds in 2 5; do
    WUJI_DATA+=("runs/unified-policy-20260930/train-data-t${seconds}/source${source}")
  done
done
"$WUJI_PYTHON" -m scripts.run_wuji_unified_job \
  --name reproduce-bc-job --gpu 0 --timeout 2400 -- PYTHON \
  -m scripts.train_wuji_unified_bc \
  --init runs/unified-policy-20260930/experts/historical.pth \
  --data "${WUJI_DATA[@]}" --output runs/unified-policy-20260930/reproduce-bc \
  --epochs 100 --save-every 50 --lr .00001 --seed 2026093001 --max-seconds 2200
```

To resume a BC artifact, use `--resume --init .../epoch_000100.pth`, a **new** output directory and an absolute end epoch greater than 100. The script restores BC Adam state and CPU/CUDA/NumPy RNG. It does not resume the source expert's PPO optimizer. A source3 BC100→101 recovery was actually run and its archived artifacts restored and checked; see `receipts/archived-model-recovery.json`. Do not interpret this example as authorization to continue this stopped research branch.

For the alternative baseline, use the original source3 expert and keep all other settings. For correction 1, `scripts.rebase_wuji_unified_normalization` rebases source3 to the historical normalizer and compensates actor/critic input layers; the operation is affine-equivalent only before clipping. For correction 2, start from the original historical expert and change only `--lr .0001`. Both corrections failed G2 and were stopped; full plans, checkpoints and fixed-budget end points are retained.

## Fixed demonstrations

`video-plan.json` freezes development rows 0, 32, 64 and 96, one per source. `scripts.audit_wuji_multigrasp --video` re-simulates them with the same selected checkpoint. `scripts.package_wuji_unified_video` arranges four columns and labels teacher, shared weights, separate simulation and each example's actual strict result. The demonstrations are not samples from the final 128-state statistics.
