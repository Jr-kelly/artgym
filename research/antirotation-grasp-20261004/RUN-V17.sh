#!/usr/bin/env bash
set -euo pipefail
# Run from the repository root, in the existing Isaac Gym Python3.8 runtime.
# Extract the runtime Release archive at the repository root first.
# Set WUJI_PYTHON to the activated compatible interpreter if needed.
wuji_python="${WUJI_PYTHON:-python}"
export PYTHONPATH=".:rl_games${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
if [[ -n "${CONDA_PREFIX:-}" ]]; then export LD_LIBRARY_PATH="$CONDA_PREFIX/lib"; fi
"$wuji_python" -m scripts.run_g2_robust_demo \
  --output "${1:-runs/antirotation-grasp-20261004/restored-v17}" \
  --grasp-plan runs/antirotation-grasp-20261004/initial-geometry-v2/projected-00/motor-plan.json \
  --table-calibration runs/antirotation-grasp-20261004/pickup-plans-v1/opposed/localization.json \
  --acquisition-path runs/antirotation-grasp-20261004/pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json \
  --seconds 36 --dx=-.1985 --dy=.05 --load .2 --detent .2 \
  --hand-friction .8 --knife-friction 1.8 --pair-force-measurement \
  --resistance-integration solver-brake --video \
  --residual-checkpoint runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth \
  --thumb-reference-override runs/antirotation-grasp-20261004/initial-geometry-v2/projected-00/reference-v1.json \
  --handover-calibration runs/antirotation-grasp-20261004/continuous-plans-v6/lower-side-calibrated/nominal-calibration.json
"$wuji_python" -m scripts.evaluate_wuji_antirotation \
  --trial "${1:-runs/antirotation-grasp-20261004/restored-v17}"
