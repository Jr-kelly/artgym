# Local policy reproduction

Worktree: `/data/research/artgym-g2-local-policy-20260928`, branch
`feat/g2-wuji-local-policy-20260928`. Physics is the effective full G2/Wuji
R3-12 scene in `configs/g2_local/physics.json`, including hand gravity off,
G2 gravity on,1000/20 arm servo, integral gain1, and original collisions.
These remain simulation assumptions, not real hardware calibration.

All output folders must be new. Existing immutable teacher is
`/data/research/artgym-experiments-20260921/runs/wuji-goal/release-core-teacher-student-20260924-v1/wuji-core-teacher-student-20260924-teacher.pth`
(SHA256 `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`).
H/S states are actual acquired frames2248/2308 from R3-12, with source trace
hash and exact ordering in `configs/g2_local/provenance.json`.

## Baselines and learning

```bash
cd /data/research/artgym-g2-local-policy-20260928
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task H --baseline fixed --output runs/g2-local-policy-20260928/my-fixed-H
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task S --baseline thumb-only --output runs/g2-local-policy-20260928/my-thumb-S
# B0: change baseline to full-teacher. Local reset is NOT table acquisition.
python3 -m scripts.g2_local_launch --name my-H-training \
  --module scripts.train_g2_local -- --task H --route support --num-envs 32 \
  --updates 240 --hours 1.5 --eval-every 25 \
  --output /data/research/artgym-g2-local-policy-20260928/runs/g2-local-policy-20260928/my-H-training
```

Launches create one source pin per version and a PID/command/log manifest.
Only send SIGTERM to a verified PID created by this task. The trainer saves
`last.pth` and status on a normal stop; `interrupted.pth` on an exception.
All runs including retries count toward12GPUh. Read `state.json` before
launching: examples are reproduction commands, not authorization to exceed
the remaining task budget.

```bash
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task H --baseline learned --num-envs 2 --episodes 2 \
  --checkpoint /absolute/path/to/checkpoint.pth --video \
  --output runs/g2-local-policy-20260928/my-learned-H
```

`learned-static` freezes the first network output, keeping the same bounded
motor ramp; this separates an improved fixed target from live feedback.
The new learner receives live simulator object state, hence privileged.
No student/deployable claim follows from its success.

## Continuous motor-only handoff

The three prefix plan files are exact copies of the successful actual
table acquisition/airflip/finger gait. No cached physics state is loaded.
Below command is implemented, and is a physical result only once a corresponding
run report exists. H can be tested by `--learned-hold-policy H.pth --only-grasp`;
S uses `--learned-operation-policy S.pth` and runs the external clock.

```bash
bash scripts/g2_local_python.sh -m scripts.run_g2_tabletop \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan configs/g2_local/prefix/acquisition-candidate2-refined-initial.json \
  --acquisition-arm-seed configs/g2_local/prefix/candidate2-arm-seed.json \
  --cartesian-acquisition --slider-face down --table-localization settled-truth \
  --air-flip 180 --lift-height .30 \
  --gait-plan configs/g2_local/prefix/candidate2-thumb-slider-contact-corridor-execution.json \
  --stay-after-gait --contact-diagnostics --seconds 20 --policy-action-mode thumb-only \
  --learned-operation-policy /absolute/path/to/S-checkpoint.pth \
  --video --closeup --output runs/g2-local-policy-20260928/my-continuous-S
```

Only the standalone local task has episode state setters. The continuous
learner runtime has no simulator handle: measured state in, motor targets out.
Initial pose reference is fixed at takeover, no rolling reference. Learner is
feedforward; frozen thumb teacher resets RNN once and records actual history.
Frozen teacher output and new support action/residual/final targets are separate
trace fields. This composite method is not the unchanged original teacher.

## Evaluation

H:22s holding. S:20s, targetlowerlimit0/+40mm, external5s reversal. Every
segment's final0.3s maxerror<10mm;2mm diagnostic separately. Entire operation
fixedworld drift<10mm, rotation<.25rad, no drop/table support. New final
placements are only authorized after a complete fixed-scene success and
must be declared before evaluation. Same-source environment replicas are
not independent placements or evidence of generalization.

`learning.jsonl`, `training-episodes.jsonl` and `eval-*.json/npz` separately
record reward, sampled rollouts, and deterministic development checks.
Source/contact cache sensitivity is documented in the result journal.
