# Restore and reproduce the unified student experiment

Use branch `feat/wuji-unified-student-20261001`. This round has its own Release,
`wuji-unified-student-20261001-v1`; earlier teacher releases remain unchanged.
Each archive contains a manifest with file sizes and SHA256 values. Restore into
a separate checkout using the standard-library-only restorer:

```bash
python3 -m scripts.restore_wuji_unified DOWNLOADED_ARCHIVE.tar.gz --output RESTORE_ROOT
```

The restorer verifies every file and refuses to overwrite different existing
contents. Archive receipt JSON files and publication verification records identify
the exact assets. The physical traces, model weights and optimizer/RNG payloads
belong in Release assets; source, data manifests, decisions and summaries belong
in Git. Reproducing a physical rollout is distinct from rescoring an archived one.

## Runtime and immutable identities

The tested H200 runtime uses Python 3.8, PyTorch 2.1.0+cu118 and the existing
IsaacGym TacSL installation. The simulator and compatible NVIDIA driver must be
installed separately. Import IsaacGym before Torch. Use the actual runtime's
prefix consistently, including its editable-package paths:

```bash
export WUJI_PYTHON=/path/to/artgym-runtime/bin/python
export PATH=/path/to/artgym-runtime/bin:$PATH
export LD_LIBRARY_PATH=/path/to/artgym-runtime/lib:$LD_LIBRARY_PATH
export PYTHONPATH="$PWD:$PWD/rl_games"
export PYTHONNOUSERSITE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2
export CUDA_VISIBLE_DEVICES=0
```

Use system Python for JSON/archive orchestration, and the scientific interpreter
for Torch/NumPy/IsaacGym scripts. `host_tool_environment.py` removes the conda
library override when invoking system SSH/rsync/gh: otherwise system SSH can load
an incompatible OpenSSL. Assets must be real files under the source root.

Every executed job has `runs/unified-student-20261001/jobs/NAME/identity.json`,
`stdout.log` and `result.json`, recording the actual command, device, start/end,
timeout, elapsed GPU time, full source hash and selected policy-file hashes.
Remote execution uses an immutable copy of the source; subsequent local analysis
changes do not change that copy. Historical host addresses are provenance, not
authorization for a new operator. The provided launcher is specific to this
session's authorized machines.

The fixed teacher is
`runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth`,
SHA256 `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8`.
The task/hand/object are respectively `wuji_multigrasp`,
`wuji_paper_official_actuator`, and `knife_wuji_bridge3_20260922`.
All formal evaluation uses seed `2026093031`, 30 Hz and the original fixed physics.
Support targets are initial issued targets + .04 × action; thumb targets are
previous issued targets + .025 × action, with original clamp/normalization.

## Training and controlled continuations

See [INPUTS.md](INPUTS.md) for the complete deployed-policy input table.
Initial55 is calibrated initial geometry/pose and joint information. S0 uses
50 × (q20, previous-action20) + initial55. SC has the same history and additionally
receives21 known controller values; masked SC keeps the same width but zeros
those values. SA uses the real SC input and adds an executed-target loss.
Only the student encoder updates; actor, teacher encoder and all shared
normalizers are frozen. C0 is one global latent; C1 maps initial55 to a latent
held constant during the episode. No model receives a source identifier.

For example, the matched action-aware continuation starts from the real6400
checkpoint and uses the following command. Change only the output name for a new
reproduction. Use target weight0 for its registered latent-only control:

```bash
"$WUJI_PYTHON" -m scripts.train_wuji_unified_student \
  --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth \
  --output runs/my-SA-12800 --kind SC --controller-mode real \
  --updates 12800 \
  --resume runs/unified-student-20261001/SC-real-6400/step_006400.pth \
  --save-at 7200 8000 9600 12800 --target-loss-weight 25 --target-loss-scale .04
```

The subsequent registered25600 continuation resumes each branch's own12800
checkpoint, with save points16000/19200/22400/25600 and the unchanged loss.
The next continuation restores each25600 checkpoint and ends at38400, with28800/32000/35200/38400 save points and unchanged settings.
The next equal continuations restore38400→51200 and51200→64000 with saves every3200updates. The final smaller64000→70400 continuation saves67200/70400. Each restores its own Adam/RNG; none adds a new experimental factor.
The repair plans record parent hashes, budgets and all controlled factors.
The action objective is latent MSE +25 × executed-target MSE/(.04 rad)².
Its forward target is the exact controller target; its backward gradient is an
explicit straight-through surrogate. Counterfactual comparisons share the same
incoming actor RNN and do not advance live state. It is not raw-mean supervision.

Each update is one actual Adam step after4 transitions in256 environments:
1024 interactions/update. Teacher latent mixing decays to zero at absolute
update400; all later training and all evaluation are pure student behavior.
Every continuation restores encoder, Adam and Python/NumPy/Torch/CUDA RNG.
Physics and current recurrent rollout state are restarted as declared new
episodes; PhysX is not serialized, so this is not bitwise uninterrupted training.

The CPU restore audit checks the saved optimizer step, identical next updates
from two restores, and repeated CPU RNG draws. It validates CUDA RNG payloads
without claiming to execute them on a CPU:

```bash
CUDA_VISIBLE_DEVICES='' "$WUJI_PYTHON" -m scripts.verify_wuji_student_checkpoint \
  PATH_TO_STUDENT.pth --output my-restore-audit.json
```

## Frozen physical evaluation and independent scoring

`data/manifest.json` identifies training/development/confirmation/final states,
their hashes and duplicate exclusions. The development set has32 states/source;
confirmation has64; final has128. These are new perturbations around the same
three grasp clusters, not unseen-grasp or unseen-object generalization. The old
teacher final set is closed. Do not use either opened final set for development.

```bash
"$WUJI_PYTHON" -m scripts.evaluate_wuji_student_batch \
  --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth \
  --models my-student=PATH_TO_STUDENT.pth \
  --states research/unified-student-20261001/data/development-all.npy \
  --output runs/my-student-development
```

The batch runs S2, S5 and F. S2/S5 are20 seconds with external2/5-second command
switches, nine final samples per stage within2mm, full validity, and body
drift<10mm/rotation<.25rad. F is40 seconds; true slider arrival within10mm for45
samples triggers the external direction switch. A complete cycle is functional
success;40-second body stability is separate. F therefore does not establish
sensor-free autonomous arrival detection by the student.

Each evaluation saves pre-reset physical trajectories, actions, targets,
slider/goal, body pose and termination reasons. Rescore without a GPU:

```bash
CUDA_VISIBLE_DEVICES='' "$WUJI_PYTHON" -m scripts.analyze_wuji_student \
  --entries teacher=PATH_TO_TEACHER_S2 teacher=PATH_TO_TEACHER_S5 teacher=PATH_TO_TEACHER_F \
    my-student=PATH_TO_STUDENT_S2 my-student=PATH_TO_STUDENT_S5 my-student=PATH_TO_STUDENT_F \
  --output my-independent-analysis
```

This independently recomputes endpoint holds, full stability and F cycles,
checks recorded counts, and writes episode CSV, Wilson intervals, paired
transitions and three-cluster summaries. An episode is the statistical unit;
stages, time samples and repeated checkpoint evaluations are correlated.
The full gate requires every source's S strict≥80%, S body≥95%, paired teacher
loss≤10/3 percentage points, and F cycle≥80%. Gates use observed proportions.

`audit_wuji_student_final` checks the frozen model/cohort/condition identities,
all512 unfiltered rows per protocol, and complete independent trial coverage.
It is a provenance/coverage audit, distinct from passing the capability gate.

## Interface and video evidence

`audit_wuji_student_inference` perturbs runtime privileged fields while replaying
nonconstant legal histories, checks full actions and actor/critic RNN states,
and counts actor teacher-encoder calls. The raw observation has138 fields;
111:137 are masked before the whole student player, while raw137 is fixed SAPG
coefficient50, not a grasp-source ID. The critic receives constant dummy values.
Known target memory initializes from issued reset commands, not measured q.

The registered video uses development rows0/32/64/96 in four columns at30fps.
Teacher and student render under matching local RTX4090 conditions because
H200 camera creation failed. These are separate rendered resimulations and
never replace H200 statistics. `package_wuji_student_video` independently
rescores every displayed result, labels actual success/failure, verifies all600
frames, and creates the paired comparison. Failed columns are retained.
Initial object pose calibration and a real slider-sensing command generator
have not been established on hardware; no video here is a hardware experiment.
