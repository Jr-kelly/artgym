# Source this file from Bash on the H100 development host.
# Override ARTGYM_RUNTIME_DIR to use another isolated Python 3.8 installation.
_wuji_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export ARTGYM_RUNTIME_DIR="${ARTGYM_RUNTIME_DIR:-$(dirname -- "$_wuji_project_dir")/artgym-runtime}"
if [[ ! -x "$ARTGYM_RUNTIME_DIR/bin/python" ]]; then
    printf 'Wuji runtime not found: %s\n' "$ARTGYM_RUNTIME_DIR" >&2
    unset _wuji_project_dir
    return 1
fi
export PATH="$ARTGYM_RUNTIME_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$ARTGYM_RUNTIME_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONNOUSERSITE=1
export MAX_JOBS="${MAX_JOBS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}"
unset _wuji_project_dir
