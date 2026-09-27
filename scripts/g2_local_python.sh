#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/home/agiuser/miniconda3/envs/artgym/bin:$PATH"
export LD_LIBRARY_PATH="/home/agiuser/miniconda3/envs/artgym/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH=".:./rl_games${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec /home/agiuser/miniconda3/envs/artgym/bin/python "$@"
