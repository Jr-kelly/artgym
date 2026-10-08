#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
inference_python="${WUJI_INFERENCE_PYTHON:-${CONDA_PREFIX:+$CONDA_PREFIX/bin/python}}"
inference_python="${inference_python:-$(command -v python)}"
inference_prefix="$(dirname "$(dirname "$inference_python")")"
export PATH="$(dirname "$inference_python"):$PATH"
export LD_LIBRARY_PATH="$inference_prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH=".:./rl_games${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec "$inference_python" "$@"
