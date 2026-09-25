# Wuji ArtManip reproduction

**2026-09-21 audit: no current run is a strict paper reproduction.** The two
multi-grasp runs are Wuji adaptations; the fixed-grasp demo-aligned run is a
diagnostic. Matching the released reward code does not establish paper-protocol
equivalence. Action scale, reward curriculum, batching, generation constraints,
and evaluation protocol differ. See [the detailed audit](paper_alignment_audit.md).
The two official generation submodules are now accessible and have been cloned
at the exact commits pinned by ArtGym; the earlier access limitation is obsolete.

Objective: a learned student policy for knife articulation with the ArtBot Wuji
right hand, following ArtManip's asset/grasp generation → SAPG teacher → latent
distillation → held-out evaluation → hardware calibration workflow.

The existing `scripts.wuji_knife_demo` is a scripted feasibility baseline and
must not be used as evidence of learned policy performance.

The current experiment uses a user-requested fingertip posture subset under
`knife_wuji_fingertip`. The earlier unfiltered run `wuji_knife_paper_sapg` was
stopped on 2026-09-20; its checkpoints are retained. See the filtering protocol
below before starting further training.

## Source and scope

- Paper: https://arxiv.org/html/2609.12498v1 (Sections 3, 4.1, 6, Appendix C).
- ArtGym source commit: `63b94fb3364596db51b7e4651b3c3c98ff994710`.
- During initial setup, requests for `youngcv/make_data` and
  `youngcv/func_lygra` failed. Rechecked on 2026-09-21: both are public and readable.
  Exact pinned revisions are now in `tmp/paper-review/upstream-make-data`
  (`eafa7b6e84811de211757119081f86b3f236495f`) and
  `tmp/paper-review/upstream-func-lygra`
  (`55f60c7e8f8db2ab55b50f6af5a07efcad191f57`). Existing data was generated with
  our local implementation and has not been regenerated with those repositories.
- Available grasp engine: https://github.com/zhaohengyin/lightning-grasp,
  commit `af43818e864b0389c97b73429e5e60de2a2de593`. Its code and generated data
  are under CC BY-NC 4.0; retain its license when using or redistributing them.
- Local object generator retains the Table 6 implementation and adds a sourced
  real-product geometry profile. Contact regions and joint placement
  are explicit local implementations made when access to the author's code failed.
- As in the paper, the object starts in a functional grasp. Autonomous pickup
  from a table is outside this experiment.
- The official knife example uses fingertip support while the thumb actuates
  the slider. Palm-enclosing power grasp is not a prerequisite for this
  reproduction. A trial palm-contact constraint was withdrawn after comparing
  the user's official-demo reference; it is not active in generation,
  validation or training. A later transition into a grip for tool use is a
  separate skill. For the preview, select the knife head toward the thumb/index
  side and verify slider travel; do not infer usefulness from holding alone.

## Fixed experiment split

`python -m scripts.generate_paper_knives` creates 35 objects under
`assets/objects/knife_wuji_paper`: 000–029 training, 030–034 held-out geometry.
`manifest.json` records dimensions, joint limits, hashes and the seed.
Following the user's request, the default `nt_a300gr` profile uses the published
NT A-300GRP overall size of 147 × 19 × 11 mm and 35 g total mass. Component
breakdown and slider footprint are estimates; see [knife_reference.md](knife_reference.md)
for the sources, exact ranges and unmeasured properties.
The full Table 6 distribution remains available using `--profile paper`.
The superseded assets/candidates are archived under
`tmp/paper-grasps/full-table6-before-size-feedback` and
`tmp/paper-grasps/provisional-slim-before-product-spec`; they cannot enter training.
Target: 1,000 candidates per object, followed by physical contact/stability
validation. Test objects must never enter teacher training or distillation.

## Differences that must remain visible

- Robot morphology: 20-DoF Wuji right hand instead of 22-DoF Sharpa left hand.
- The current geometry distribution is narrowed to the user's intended slim
  utility knife and uses a fixed nominal anchor, rather than reproducing the
  entire Table 6 distribution. The training/grasp/distillation method is retained.
- Hand convex collision geometry is derived from ArtBot visual meshes. Source
  masses/gains are not hardware-calibrated. `hand=wuji_paper` enables cross-finger
  and distal-to-palm collision while excluding same-finger and proximal-to-palm
  pairs, matching the grasp generator's filter. Base `hand=wuji` retains the
  ArtBot source's disabled self-collision setting for the old baseline.
- Paper friction 2–4 and prismatic damping 700–1300 are effective values selected
  through Sharpa real-object calibration. They are an initial reproduction
  baseline, not identified Wuji/knife physical parameters.
- Knife mass now totals 35 g, with an estimated 29/6 g component split and ±30%
  randomization per component, rather than the paper's heavier Sharpa range.
- Paper uses 20,000 environments, two RTX 5090 GPUs and about 2B steps / 48 h.
  The local run uses one 24 GB RTX 4090; the remote development host has four
  H100 80 GB GPUs. Actual sample budgets, wall time and evaluation results must
  be reported separately; the four-GPU setup is described below.
- A reference knife has been selected from public specifications. The actually
  available physical specimen, Wuji SDK path and sensor configuration remain
  unknown. No hardware command is issued by data generation or training.

## Completion evidence

Required artifacts are a nonempty physically validated grasp pool, a trained
teacher checkpoint, a distilled student artifact, evaluation on held-out objects
and grasps with randomized physics, and videos driven by those checkpoints.
Training runs or low distillation loss alone are not task success. Hardware
readiness additionally requires a verified joint mapping, observation parity,
latency/control-rate checks and calibration on a separate real knife.

## Local implementation and checks (2026-09-20)

- `scripts/generate_paper_knives.py`: generated all 35 assets. Unit checks pass
  for the published dimension ranges, URDF limits, split isolation and contact
  masks. Knife placement along the handle is a documented local convention.
- `scripts/generate_functional_wuji_grasps.py`: Wuji contact field, semantic
  masking, wrench search, GPU IK, allowed-pad projection and collision filtering
  using the public Lightning Grasp engine. All 35 geometries completed generation
  and the original validation: 35,000 candidates, 3,194 valid grasps; 2,161 training
  grasps and 545 test grasps on the 30 training geometries, plus 488 valid grasps
  on the five held-out geometries.
  Debug fields with fewer than 80,000 samples cannot pass the training preflight.
  CUDA kernels loaded successfully in Python 3.10 / PyTorch 2.8.0+cu128. Before
  the final product selection, the provisional slim anchor produced 1,000
  candidates and 88 valid grasps (70 train / 18 test), including filtered
  self-collision. This count does NOT apply to the regenerated NT reference.
  The final NT reference anchor has now produced **1,000 candidates and 84 valid
  grasps (67 train / 17 test)** with 35 g nominal total mass, gravity and filtered
  self-collision. These are the original counts before the posture subset.
- `scripts/validate_paper_grasps.py`: original ArtGrasp physical validation for
  30 control steps (1 s), five required functional contacts, gravity on. Keeps
  the upstream 5 cm / 1.57 rad drift limits; these are generation acceptance
  limits, not claimed real-hardware precision. No external random force is used
  during this initial validation. Training/evaluation enable randomization.
- `isaacgymenvs/deploy/wuji/observation_provider.py`: strict 20-DoF observation
  assembler requiring initial geometry in hand-base coordinates. Three-step
  comparison against Isaac Gym passed for every policy and student input;
  finger link origins agree with simulator FK. This is offline input parity,
  not an SDK connection or real-hand test.
- The earlier bootstrap checkpoint really contains 40 Adam optimizer steps
  across 20 epochs / 81,920 transitions. It remains a smoke test on the old
  simplified object, not a teacher for this reproduction.
- A separate three-epoch SAPG integration check on the legacy object passed:
  five exploration groups, 20 actions, 72 Adam updates, finite model weights,
  30,720 transitions. This confirms the algorithm update path only. It does not
  establish skill on the NT reference.

## User-requested fingertip posture filtering

`scripts/filter_wuji_fingertip_grasps.py` filters the original full 75-column
states without changing joint targets, object poses, geometry or physical
parameters. Reference: original geometry 000, valid grasp 52, used by the approved
scripted video. This is a local task restriction, not an original paper threshold.

1. Knife extension axis points toward hand +Y (thumb/index side), dot ≥ 0.82;
   orientation differs from the reference by ≤ 40°, center by ≤ 35 mm, and
   center height above the hand base is ≥ 95 mm.
2. Thumb IK follows nine 5 mm-spaced slider points over 40 mm extension and
   eight return points, within joint limits, with support-surface position error
   ≤ 2 mm. It tries three contact locations inside the slider. This approximate
   kinematic screen does not prove collision-free travel, adequate pushing force,
   or successful dynamic manipulation.
3. Revalidate each unchanged initial state for 60 control steps (2 s) in ArtGrasp:
   object gravity, cross-finger self-collision, nominal friction 3 and slider
   damping 1000; no external force or domain randomization during this check.
   Sample contacts every three control steps (20 samples). Each required contact
   must occur in ≥ 90% of samples: thumb–slider and all four other pads–handle.
   All five must be present at the final sample. No sampled palm–object contact;
   maximum handle drift ≤ 10 mm and rotation ≤ 0.25 rad. The sampled object pose
   must also keep satisfying the reference posture limits.

These tests measure stability at the initial grasp, not a policy-driven push/pull
cycle. The preview's intermittent ring-finger contact during motion is therefore
not evidence of passing a continuous-contact manipulation test.

The separate assets and caches are `assets/objects/knife_wuji_fingertip` and
`caches/initial_grasp/wuji/knife_wuji_fingertip`. Original train/test membership
is preserved exactly; held-out geometries 030–034 never enter training or
distillation. The preflight checks source/subset equality, split separation,
hashes of meshes/configuration/validation code, physical reports, and at least
10 training grasps plus one test grasp per training geometry. It rejects stale
or altered output. `dataset-report.json` records final per-geometry counts;
`tmp/wuji-fingertip-filter/all-35-grasps.jpg` shows one accepted grasp per geometry.

Completed 2026-09-20: 3,194 original valid grasps → 1,325 posture-eligible →
1,256 thumb-reachable → **1,187 physically revalidated grasps**, with all 35
geometries retained. The 30 training geometries provide **811 train / 190 test**
grasps; the five held-out geometries provide **186**. The smallest training
pool has 14 grasps. No test grasp was reassigned and no replacement candidates
were needed. The approved reference 000/52 remains accepted.

Three regression checks pass: approved/reversed/displaced/low posture cases,
split overlap and altered-state rejection, and thumb-chain FK agreement with
the complete hand at 100 configurations. All source/subset and physical-report
checks passed before starting `wuji_knife_fingertip_sapg` from random weights.
This is a running training experiment; successful policy cycles, student
distillation and real-hardware validation remain pending.

```bash
source /home/agiuser/miniconda3/etc/profile.d/conda.sh
conda activate artgym
python -m scripts.filter_wuji_fingertip_grasps prepare
python -m scripts.filter_wuji_fingertip_grasps screen --instances all
MAX_JOBS=2 OMP_NUM_THREADS=4 python -m scripts.run_wuji_fingertip_filter
python -m scripts.filter_wuji_fingertip_grasps check

# New experiment from random initialization, following a successful preflight.
MAX_JOBS=2 OMP_NUM_THREADS=4 python -m scripts.run_wuji_paper_pipeline \
  --fingertip-filter --run-dir runs/wuji_knife_fingertip_sapg
```

Teacher, student distillation, anchor evaluation, held-out evaluation and learned
video generation all use the filtered object configuration in this pipeline.
The existing preview video remains separate from policy evaluation.

## Commands

Separate Python environments are necessary: Isaac Gym uses Python 3.8 (local
PyTorch CUDA 11.8, remote H100 PyTorch CUDA 12.1), while the available Lightning
Grasp kernels use Python 3.10 / CUDA 12.

```bash
# Grasp generation (after the Lightning Grasp environment setup completes).
tmp/lygra-env/bin/python -m scripts.check_lygra_setup --fix-urdfpy-numpy
tmp/lygra-env/bin/python -m scripts.generate_functional_wuji_grasps --instances all --count 1000

source /home/agiuser/miniconda3/etc/profile.d/conda.sh
conda activate artgym
python -m scripts.validate_paper_grasps
python -m scripts.validate_paper_grasps --check-training-ready

# Current user-specific run: complete the fingertip filtering commands above first.
MAX_JOBS=2 python -m isaacgymenvs.train hand=wuji_paper object=knife_wuji_fingertip \
  train=wujiKnifeSAPG num_envs=2560 headless=True pipeline=gpu \
  experiment=wuji_knife_fingertip_sapg seed=20260920
```

The teacher configuration uses 5 exploration groups of 512 environments,
40,960 on-policy transitions per epoch and minibatches of 8,192. Its default
50,000-epoch budget corresponds to about 2.048 billion on-policy transitions;
actual throughput and convergence must be measured on this RTX 4090.

`scripts/run_wuji_paper_pipeline.py` runs generation and validation per instance,
then dataset preflight, teacher training, teacher evaluation on held-out grasps
of training anchor 000, MSE-only student distillation, evaluation of both models
on the five held-out geometries, and a student-checkpoint-driven video. A teacher
or student with no grasp averaging one complete cycle across five trials stops
the pipeline for further work; passing that minimal gate is not a hardware claim.

The filtered experiment directory is `runs/wuji_knife_fingertip_sapg`. `pipeline-status.json`
records stage commands, PIDs, timestamps and failures; each stage has its own log.
`pipeline.log` records stage transitions. The process is detached from the terminal.

```bash
tail -f runs/wuji_knife_fingertip_sapg/pipeline.log
tail -f runs/wuji_knife_fingertip_sapg/teacher.log  # after data preparation
```

## Four-GPU teacher training

Use four GPUs allocated to the same node. Each process owns one Isaac Gym
simulation and uses its matching CUDA device. NCCL synchronizes gradients and
normalization statistics; each GPU has five SAPG exploration groups and samples
the training pool independently. Experience reuse stays within each GPU's SAPG
groups. Only rank 0 writes logs/checkpoints; full per-rank checkpoints are gathered
on CPU through Gloo when needed. Torchrun supplies the rendezvous port.

On the four-H100 development host (`ssh -p 30296 wangjiarui@10.14.0.73`),
the isolated runtime is `/home/wangjiarui/artgym-runtime`. It contains Python
3.8.20, PyTorch 2.1.0+cu121 and the same Isaac Gym TacSL runtime used locally.
The activation helper sets the Python/library paths and thread limits:

```bash
cd /home/wangjiarui/artgym
source scripts/activate_wuji_runtime.sh
MAX_JOBS=2 OMP_NUM_THREADS=4 python -m scripts.run_wuji_paper_pipeline \
  --fingertip-filter --gpus 4 --periodic-eval --eval-gpu 3 \
  --run-dir runs/wuji_knife_fingertip_4gpu
```

The runtime is installed on this development host. Installation on another host
is described in `install.md`; `transfer/environment/h100-installed.txt` records
the exact deployed packages. The launcher checks the number of visible CUDA
devices before starting; it rejects a four-GPU request when the allocation
exposes fewer than four. Add `--dry-run` to inspect
the command and sample budget without loading the simulator or starting work.

| Setting | One GPU default | Four GPUs default |
| --- | ---: | ---: |
| Environments per GPU | 2,560 | 2,560 |
| Total environments | 2,560 | 10,240 |
| Global transitions per epoch | 40,960 | 163,840 |
| Total transition budget | 2,048,000,000 | 2,048,000,000 |
| Maximum epochs | 50,000 | 12,500 |
| Minibatch per GPU | 8,192 | 8,192 |
| Global minibatch | 8,192 | 32,768 |

`--total-steps` sets a global budget, while `--epochs` explicitly sets update
epochs at the chosen GPU count. They are mutually exclusive. A non-divisible
step budget rounds up to one complete rollout. `--envs-per-gpu` must be divisible
by five; the launcher derives the SAPG group and minibatch sizes. Learning rate
stays 2e-4. Equal interaction budgets do not imply identical optimization:
four-GPU defaults use larger global minibatches and fewer updates. Reward
curriculum milestones scale with the global batch, preserving their approximate
interaction counts (four-GPU warmup 50 epochs, final weights at 500 epochs).

Teacher completion is followed by single-GPU evaluation and single-GPU student
distillation, then held-out evaluation and video using the existing quality gates.
The measured short-run throughput below estimates budget duration; convergence
and held-out success must be assessed separately.

For a short budget, for example:

```bash
python -m scripts.run_wuji_paper_pipeline --fingertip-filter --gpus 4 \
  --total-steps 163840000 --run-dir runs/wuji_knife_4gpu_1000epochs
```

For continuation on the same number of GPUs/environments, provide `--checkpoint`
and a new run directory. Global counters and optimizer state are restored; the
budget remains an absolute total, not an additional number of steps. PhysX state
is not serialized, so rollout and recurrent state reset together on continuation.
For a change from one GPU to four, use `--checkpoint PATH --weights-only`: this
loads the shared model and normalization weights into every rank, resets the
optimizer/counters, and starts a new budget. A mismatched full resume is rejected.

Validation performed locally: four CPU processes running the actual SAPG
optimizer on synthetic Wuji-shaped inputs, synchronized parameters/normalizers,
identical global frame counters, independent rollout data, four-rank checkpoint
restore, and explicit one-to-four-rank warm start. A real Isaac Gym single-GPU
check on the filtered dataset completed three epochs / 1,920 transitions with
finite weights. On 2026-09-20, the four-H100 host also passed real GPU PhysX
training with 40 environments per rank: three epochs / 7,680 global transitions,
then a full checkpoint continuation to five epochs / 12,800 transitions. Adam
updates increased from 72 to 120. Four-rank model and normalization tensors and
optimizer states were identical, while per-rank observations were distinct and
finite. Loading the transferred single-GPU checkpoint with `--weights-only`
passed two new epochs / 5,120 transitions with fresh counters and 48 updates.
These checks validate training infrastructure; they do not establish a learned
knife manipulation skill or real-hardware readiness. Simulation camera rendering
was not included in the H100 checks.

The default 4 × 2,560-environment benchmark completed 30 epochs / 4,915,200
transitions and 720 Adam updates per rank. The final checkpoint passed the same
finite/synchronized-weights and independent-observations audit. Excluding the
first five epochs, throughput measured between TensorBoard epoch timestamps was
**14,555 global transitions/s** (logged median 14,230/s), including time between
epochs. Peak sampled GPU memory was 9,285 MiB. The whole process, including
startup and final checkpoint writing, took 372.6 s. At that short-run throughput,
the 2.048B-step budget would take approximately **39.1 hours**; later policy
dynamics and checkpoint overhead can change this, and the estimate does not
promise convergence. The subsequent production launch is recorded below.

Remote artifacts: `runs/wuji_4h100_benchmark_2560_20260920/teacher.log`,
`benchmark-summary.json`, `debug-report.json`, and `checkpoint-audit.json` in
that run directory; overall results are in `transfer/wuji-multigpu-verification.json`.
`tests/check_distributed_checkpoint.py` can audit future real SAPG checkpoints.

```bash
python -m unittest discover -s tests -p test_wuji_multigpu.py -v
OMP_NUM_THREADS=1 python -m torch.distributed.run --standalone --nnodes=1 \
  --nproc_per_node=4 tests/distributed_sapg_worker.py --output tmp/four-rank-check
```

## Checkpoints and evaluation during teacher training

The Wuji teacher saves complete rank-indexed recovery state at epoch 10, every
50 epochs, and the final epoch. `checkpoints/latest.pth` atomically points to the
latest complete snapshot. Keep the latest six snapshots and all multiples of
500 plus the final snapshot; training-reward best remains in `nn/<run>.pth`.
Checkpoint writes use a temporary file, flush/fsync, and atomic replacement,
so evaluators and resume jobs never see a partially overwritten checkpoint.
Full checkpoints contain all ranks' optimizer and rollout bookkeeping; PhysX
still resets on resume as described above.

Epoch 10, every 100 epochs, and the final epoch also publish immutable policy-only
snapshots in `evaluation/inbox/`. `--periodic-eval --eval-gpu 3` starts one separate
evaluator sharing the fourth GPU. It uses geometries 000, 010, 020, their test
grasps, five parallel randomized trials per grasp, deterministic leader actions,
seed 20260921 and a 1,200-step budget. This is a fixed monitoring panel, not an
all-geometry test. Held-out geometries 030–034 remain excluded from selection.
The evaluator can briefly reduce training throughput. If it falls behind, it
records older pending snapshots as skipped and evaluates the newest one.

`evaluation/latest.json` reports the latest successful evaluation, including
complete open-close cycle success rate, mean cycles, and per-object results.
`evaluation/history.jsonl` also records evaluation failures. Each evaluated epoch
has its own logs/results directory. `evaluation/best.pth` points to the policy
with the highest trial success rate, using mean cycles to break ties. This file
is for inference/distillation or a weights-only warm start; for full training
continuation use `checkpoints/latest.pth` or a retained complete snapshot.
The pipeline waits for the final periodic evaluation and uses the evaluated best
policy for its existing teacher gate and distillation. A zero-success evaluation
is recorded normally and does not stop ongoing teacher training.

At the pre-evaluation benchmark speed, saving every 50 epochs is about 10 minutes,
and evaluation every 100 is about 20 minutes. These are approximate times; the
actual schedule uses epochs. Configuration keys live in `wujiKnifeSAPG.yaml`.

```bash
# On the four-H100 host, after activation:
tail -f runs/wuji_knife_fingertip_4gpu/teacher.log
cat runs/wuji_knife_fingertip_4gpu/checkpoints/latest.json
cat runs/wuji_knife_fingertip_4gpu/evaluation/status.json
cat runs/wuji_knife_fingertip_4gpu/evaluation/latest.json
```

Production started on 2026-09-20 at 13:36 UTC (21:36 China time), from random
initialization, under `/home/wangjiarui/artgym/runs/wuji_knife_fingertip_4gpu`.
It uses 4 × 2,560 environments, a 2.048B-step / 12,500-epoch budget, and the
periodic evaluator above. Launch metadata is in `transfer/production-launch.json`.
The independent local 4090 experiment remains running. The prior 39-hour
estimate was measured without periodic evaluation, so allow additional time.
