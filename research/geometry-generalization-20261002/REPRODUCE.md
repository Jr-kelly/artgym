# Restore and reproduce the geometry round

Use the independent branch `feat/wuji-geometry-generalization-20261002`, based on the completed student branch `e6c9f3e0d6167b0df529a5e7d75c88b91ff42613`. Earlier final cohorts and releases remain closed. This round has no old wall-clock deadline. It inherits the cumulative 64 GPU-hour limit and 32.4534053852823 GPU-hours of prior consumption. Current receipts and `STATE.json` give the new consumption.

## Restore the exact frozen parents and controlled assets

The release tag is `wuji-geometry-generalization-20261002-v1`. Until `STATE.json` records public verification, it is a draft; do not interpret these eventual public commands as proof that publication is already complete.

```bash
git clone --branch feat/wuji-geometry-generalization-20261002 \
  https://github.com/Jr-kelly/artgym.git artgym-geometry
cd artgym-geometry
curl -fL -o geometry-frozen-parent-models.tar.gz \
  https://github.com/Jr-kelly/artgym/releases/download/wuji-geometry-generalization-20261002-v1/geometry-frozen-parent-models.tar.gz
curl -fL -o geometry-controlled-assets-v1.tar.gz \
  https://github.com/Jr-kelly/artgym/releases/download/wuji-geometry-generalization-20261002-v1/geometry-controlled-assets-v1.tar.gz
sha256sum -c <<'SHA'
5c5a1a91db8807473beccdc3f1f990036d4f5f036ef153b222e3c3825bb3e612  geometry-frozen-parent-models.tar.gz
55ac39c85a374f0294619967b0f34bf7d6ef0eaad98025eb81a9c6b6cdb8c575  geometry-controlled-assets-v1.tar.gz
SHA
python3 -m scripts.restore_wuji_unified geometry-frozen-parent-models.tar.gz --output .
python3 -m scripts.restore_wuji_unified geometry-controlled-assets-v1.tar.gz --output .
```

Use a plain clone. The optional legacy `func_lygra`/`make_data` SSH submodules are not required by this runtime. The main Git tree already tracks `rl_games`, baseline hand assets, quaternion-reference caches and the default original training seeds. The two bundles supply the exact teacher, SA51200 checkpoint and sidecar, controlled assets, caches, adapted seeds and explicit new data splits. Restoration verifies every archived file and refuses to overwrite different existing bytes. Keep prior user work in a separate checkout. The old primary release remains preserved and is not required for this restoration chain.

The parent checkpoint includes Adam and RNG state. Its CPU recovery audit restores optimizer state and reproduces a synthetic test update/RNG stream on two disposable in-memory copies; the stored next optimization step is51201. No training update was applied to the research candidate or checkpoint files. CUDA RNG payloads were preserved but were not executed by that CPU audit.

## Runtime and a minimal paired evaluation

The measured H200 environment is Python3.8.20, PyTorch2.1.0+cu118, NumPy1.23.5, SciPy1.10.1, driver570.133.20 and the existing IsaacGym TacSL installation. Timestamped inventories are `runtime-pip-freeze.txt`, `runtime-gpu-driver.csv` and `runtime-provenance.json`. Supply a compatible configured runtime independently; the licensed IsaacGym installation is not redistributed. Import IsaacGym before PyTorch in scientific entrypoints, as `wuji_goal_common` does.

```bash
export PATH=/path/to/runtime/bin:$PATH
export LD_LIBRARY_PATH=/path/to/runtime/lib:$LD_LIBRARY_PATH
export PYTHONPATH="$PWD:$PWD/rl_games"
export PYTHONNOUSERSITE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2
export CUDA_VISIBLE_DEVICES=0
/path/to/runtime/bin/python -m scripts.static_wuji_geometry \
  --label T90 --split screen-attempts --take 16 --output runs/my-T90-static
/path/to/runtime/bin/python -m scripts.evaluate_wuji_geometry \
  --label T90 --states runs/my-T90-static/valid-states.npy \
  --model teacher --protocol S2 --output runs/my-T90-teacher-S2
/path/to/runtime/bin/python -m scripts.evaluate_wuji_geometry \
  --label T90 --states runs/my-T90-static/valid-states.npy \
  --model student --protocol S2 --output runs/my-T90-student-S2
```

Use new output directories. Pair exactly the same statically accepted array; selection is never based on policy success. Missing sources are grasp-adaptation coverage gaps, not manipulation success of0%. No padding enters denominators.

URDF axis order is width/thickness/length; policy preprocessing transforms bbox to width/length/thickness. `BASELINE_PHYSICS.json` records the measured original actor masses, effective inertias and joint parameters. `WujiGeometry` freezes effective inertia with `recompute=False` after IsaacGym's shape-based inertia calculation; retaining authored URDF inertia alone is insufficient. Slider size, travel, physics and control stay fixed. The handle-length anchor is its center, with fixed longitudinal slider-joint origin. Thickness moves jointY by half the thickness change. Every initialization cache must declare `hand_base` pose coordinates; omitting that metadata produced the retained early infrastructure failure.

The parameterized generator `prepare_wuji_geometry` refuses to overwrite assets. Restore prepared datasets for exact reproduction. Generating from scratch requires first measuring the baseline physics and registering a new output namespace; it is not a way to replace this round's frozen data.

S2/S5 run20 seconds with a fixed external2/5-second clock. Every stage's last9 samples must have error<2mm, with full validity and body translation<10mm/rotation<0.25rad. F runs40 seconds using the inherited true-slider arrival scheduler (<10mm for45 samples), and requires at least one open-close cycle. Full-horizon holding is a separate result. F does not prove sensor-free arrival detection.

## Final choice, raw evidence and independent rescoring

The final candidate is unchanged SA51200. The registered two-second learner-prefix teacher-latent diagnostic failed its prerequisite at W120 source3. No new optimization or same-budget training control was triggered. `final-freeze.json` stores model, asset, initialization-recipe, data, source and plan hashes. `FINAL_PLAN.json` specifies final seed2026100204,192 static attempts and up to128 accepted states per source. Zero or incomplete coverage retains the actual denominator. Final results cannot select, repair or train a candidate.

Restore the screen, per-geometry confirm64, privileged diagnostic and per-geometry final bundles into their original `runs/geometry-generalization-20261002/` namespaces. The static/video/restore/job bundle retains selections, attempted states and earlier failures. Changed-inertia early statics are supplementary, rather than main controlled results. Final packets also contain their corresponding static acceptance evidence and completed job receipt.

```bash
CUDA_VISIBLE_DEVICES='' /path/to/runtime/bin/python -m scripts.analyze_wuji_geometry \
  --prefix final- --output research/geometry-generalization-20261002/final-analysis
/path/to/runtime/bin/python -m scripts.summarize_wuji_geometry_report \
  --analysis research/geometry-generalization-20261002/final-analysis \
  --output research/geometry-generalization-20261002/FINAL_TABLES.md \
  --title '独立最终评测' --static-suffix static-final
/path/to/runtime/bin/python -m scripts.plot_wuji_geometry \
  --analysis research/geometry-generalization-20261002/final-analysis \
  --output research/geometry-generalization-20261002/figures/final --stage final
```

The analyzer independently recomputes endpoint, F-cycle and body scores from raw traces, verifies recorded counts and model hashes, and emits episode CSV, Wilson95 cell intervals, paired transitions and bootstrap differences. Geometry/source macros show complete coverage separately from available-source-only coverage. Geometries share perturbation lineage where selected attempt rows overlap, while their adapted physical states differ. Reusing one initial state in several protocols does not create independent initial-grasp samples. Additional report/figure builders reside in this research directory and do not alter the frozen scientific runtime.

Every GPU job has an immutable code/config/asset copy, bounded timeout, command/model/source/device identity, stdout and start/end/exit/GPU-time receipt. Actual source versions are retained in source-pin packets. Reconstruct each listed Python/YAML path from `blobs/<sha256>` and verify the per-job aggregate. A later branch version is not a substitute for an earlier pin. Configs, assets and weights are retained separately. The controller launchers target only the host authorized in this session; a historical address does not authorize another operator to connect. Direct scientific commands can run in an equivalent independently configured environment.

## Offline interface and limitations

`WujiTemporalPolicyRuntime.reset` accepts initial q, calibrated body/slider poses, raw URDF bboxes and initial issued joint targets. Poses use hand-base coordinates and xyzw quaternions; joint order follows the official actuator config. `step` accepts measured q, external goal and optional replayed actual previous action/issued target. External goal is a displacement relative to the initially calibrated slider position, in metres:0 or0.04. The caller generates commands and detects arrival independently.

The interface maintains50-step history, previous action, issued targets and RNN state, including partial reset. It uses FK and initial calibration, without current object/slider/contact truth. It outputs actions and targets and never sends hardware commands.

CPU original-player parity passed on80 nonconstant steps and partial resets. Actual H200 inputs replayed on CPU did not meet cross-device tolerance; identical network input/incoming RNN also retained a numerical discrepancy. Keep the negative `physical-legal-replay-audit-v1.json` and exact-input diagnostic. Backend/device differences are an explanation supported by that diagnostic; TF32 causality was not directly established.

Source/assets, static initialization, frozen H200 screening, independent confirmation/final, privileged diagnosis, CPU replay and separately rendered RTX4090 resimulation videos are distinct evidence. No robot was driven. No autonomous grasping, paper cutting or sim2real result is claimed. The final report states the remaining calibration and physical-measurement requirements.

The CSV field `worst_stage_tail_mean_error_m` is an auxiliary recorded-window diagnostic: truncated runs can include partial or inactive tail windows. It is not the strict score or a fair full-stage accuracy estimate. The main endpoint/F-cycle scores and body counts are independently recomputed; mean/max error uses active recorded samples. Frame k is recorded after physics and has time(k+1)/30 seconds.
