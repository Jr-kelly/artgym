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

## Final training configuration B4

This is a new privileged joint controller around a motor-only geometric thumb
path; it does not execute the frozen teacher thumb. Original models remain
unchanged. The path alone held the knife but lost slider contact (R3-05).
Support and thumb residuals have0.20rad span and0.60rad/s slew; total thumb
motor increments are capped0.025rad/control and original asset joint limits.

```bash
python3 -m scripts.g2_local_launch --name my-B4 \
  --module scripts.train_g2_local -- --task S --route joint --num-envs 32 \
  --updates 600 --hours 2.5 --eval-every 25 \
  --checkpoint /data/research/artgym-g2-local-policy-20260928/runs/g2-local-policy-20260928/A1-H-main/checkpoint-00010.pth \
  --thumb-plan /data/research/artgym-g2-local-policy-20260928/configs/g2_local/thumb-material-path.json \
  --initial-support-std .10 --initial-thumb-std .15 \
  --output /data/research/artgym-g2-local-policy-20260928/runs/g2-local-policy-20260928/my-B4

bash scripts/g2_local_python.sh -m scripts.run_g2_local --task S \
  --baseline learned --checkpoint /absolute/path/to/B4-checkpoint.pth \
  --video --output runs/g2-local-policy-20260928/my-B4-evaluation
```

The standalone runner and continuous runtime recover the thumb motor plan
from checkpoint metadata, so evaluation cannot silently revert to frozen
teacher control. All these are reproduction examples; check cumulative budgets
before starting new work. No complete Ssuccess is asserted by these commands.

Read-only continuous handoff audit (no simulation):
```bash
bash scripts/g2_local_python.sh -m scripts.audit_g2_continuous_local \
  --run runs/g2-local-policy-20260928/R4-02-continuous-joint-S-cp25 \
  --evaluation runs/g2-local-policy-20260928/B4-S-joint-path/eval-00025.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --output runs/g2-local-policy-20260928/R4-02-handoff-audit-reproduced.json
```
R4-03 uses the exact R4-02 launch arguments plus `--local-reset-quaternion-compat` and a fresh output directory. This opt-in only aligns the first measured wrist quaternion sign to the legacy local reset representation; subsequent observations use native PhysX signs. Old result/source pins remain untouched.

## Actual prepared-state local evaluation and continuous counterpart

R7 uses Hpilot10 after acquisition, then B4cp25 after22s hold and2s actual
settling. Both are frozen new privileged networks. The original actor is not
executed during B4operation. These commands do not imply continuous success
until its report/audit passes. The state below was extracted from the actual
R2-04 finalframe2968, not made by interpolation.

```bash
cd /data/research/artgym-g2-local-policy-20260928
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task S --baseline learned --num-envs 1 --episodes 2 \
  --state configs/g2_local/S-after-continuous-learned-H-state.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --video --output runs/g2-local-policy-20260928/my-prepared-S

bash scripts/g2_local_python.sh -m scripts.run_g2_tabletop \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan configs/g2_local/prefix/acquisition-candidate2-refined-initial.json \
  --acquisition-arm-seed configs/g2_local/prefix/candidate2-arm-seed.json \
  --cartesian-acquisition --slider-face down --table-localization settled-truth \
  --air-flip 180 --lift-height .30 \
  --gait-plan configs/g2_local/prefix/candidate2-thumb-slider-contact-corridor-execution.json \
  --stay-after-gait --contact-diagnostics --seconds 20 --policy-action-mode thumb-only \
  --learned-hold-policy runs/g2-local-policy-20260928/A1-H-pilot/checkpoint-00010.pth \
  --learned-operation-policy runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --local-reset-quaternion-compat --video --closeup \
  --output runs/g2-local-policy-20260928/my-continuous-prepared-S
```

New checkpoints/raw development evidence are in the baseline and B4/R4-R6
increment archives on Releasev1. Extract them in the stated runroot, in that
order. Frozen source pins, all failures and independent raw scorers are included.
`audit_g2_gpu_budget.py` merges our process intervals on the single GPU and
conservatively includes all control/evaluation simulations plus0.25hdebug;
concurrent processes do not count as extra physical GPUs.

The20-placement validation driver refuses declaration without an actual
continuous success and its independent audit, and refuses execution until the
manifest is committed and pushed. The manifest was committed/pushed as8c4cce1 before launch. Use a fresh declared manifest/run namespace for any new validation; never overwrite the recorded20 placements.


## Frozen-input and hand-gravity local diagnostics

Round8 does not train or change the frozen model. These are local resets from an actually reached
H-prepared state, not continuous tabletop success. Both input variants require one ideal initial
knife pose and slider value. The proprioceptive variant removes later live object/slider feedback
only during S; the preceding acquisition/H pipeline is still privileged.

```bash
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task S --baseline learned --num-envs 2 --episodes 1 \
  --state configs/g2_local/S-after-continuous-learned-H-state.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --input-ablation fixed-body-proprio-slider --video \
  --output runs/g2-local-policy-20260928/my-proprio-input-test
```

Use `--input-ablation fixed-body-live-slider` for the body-only ablation. For the independent
hand-gravity sensitivity, remove `--input-ablation` and add `--hand-gravity`; retain all other options.
Each output records actual input observations, raw physical traces, contacts and gravity flags.
`score_g2_local_trace` independently evaluates `episode-000.npz` with `--task S` and the same `--source` state.
The robot FK/quaternion audit can be repeated without simulation using `scripts.audit_g2_input_ablation`.

The alternate gait controller uses `--gait-arm-retarget-reference configs/g2_local/gait-nominal-start.json`
on the continuous command above. It preserves hand commands/gates and transforms the nominal wrist path
at the actual gait motor-reference boundary. This is a separately named development variant; its
geometric prechecks do not establish physical success and it is not part of the frozen validation.


## Separate hand-gravity motor compensation diagnostic

```bash
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task S --baseline learned --num-envs 2 --episodes 1 \
  --state configs/g2_local/S-after-continuous-learned-H-state.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --hand-gravity --hand-gravity-compensation --video \
  --output runs/g2-local-policy-20260928/my-gravity-motor-S
```

R10-01 passes2/2 local S under hand gravity ON; no continuous gravity-ON success is established yet.
The bias is URDF-modeled static gravity torque / actual per-joint position stiffness, capped±.08rad.
This changes robot motor targets only, with original total .02/.025rad per-step support/thumb slew and
joint limits. Mass/COM values are checked against loaded simulator properties; gains, effort limits,
friction and all other physical parameters remain unchanged. H uses `--task H`, the default actual
H state (remove the S `--state` option), and A1-H-pilot/checkpoint-00010.pth. The paired H without
feedforward omits only `--hand-gravity-compensation`.

The policy observes nominal pre-feedforward targets. Raw actuator targets and
`hand_gravity_model_torque` / `hand_gravity_applied_motor_bias` are separately saved. These torques
are model predictions, not measurements; this is neither hidden applied force nor real calibration.

The separate continuous gait variant adds `--gait-translation-before-alignment` alongside the
retarget option. It may physically translate the held knife toward the original fixed gait reference
by at most4mm over1s, hold1s, and then apply the **unchanged** original5mm alignment gate. The
planned knife trajectory and actual tracking/fixed-reference errors are saved. It cannot reset poses,
refresh the scoring reference or relax the alignment gate. R9-04 passed that alignment and then failed small-finger support; its later R12 contact variant is separately labeled.

## Hand-gravity and acquisition follow-ups

R10 is a local reset condition. Use the same H/S commands above with
`--hand-gravity`, then add `--hand-gravity-compensation` for the paired
motor feedforward condition. H uses `configs/g2_local/H-actual-state.npz`;
S uses `configs/g2_local/S-after-continuous-learned-H-state.npz`.
Do not call these tabletop results. Both flags also exist on the continuous
runner: gravity and compensation start at the FIRST physical step and stay
on. Full gravity-ON acquisition failed, despite local H/S passes.

Every trial has an exact `*-launch.json` containing immutable source pin,
complete argument list, checkpoint paths and output folder. To reproduce a
recorded diagnostic with a new name (check the remaining budget first):

```bash
python3 - <<'PY_REPLAY'
import json, pathlib, subprocess
root = pathlib.Path('/data/research/artgym-g2-local-policy-20260928')
runroot = root / 'runs/g2-local-policy-20260928'
source = runroot / 'R11-02-continuous-gravity-on-motor-feedforward-launch.json'
record = json.loads(source.read_text())
name = 'my-gravity-continuous-repeat'
args = record['command'][4:]
args[args.index('--output') + 1] = str(runroot / name)
# Reuses the documented arguments. Current scripts receive a NEW immutable pin.
subprocess.run(['python3', str(root / 'scripts/g2_local_launch.py'),
                '--name', name, '--module', record['module'], '--'] + args,
               cwd=root, check=True)
PY_REPLAY
```

For an EXACT old runtime, execute `record['command']` with only its output
changed under `record['cwd']`, using the environment in `g2_local_launch.py`;
do not claim current-branch replay as an identical old source pin.
R11-03 adds only `--gait-arm-retarget-reference configs/g2_local/gait-nominal-start.json`.
R12-01 reproduces the R9-04 seen-placement launch plus `--gait-pinky-retarget`.
This last flag uses one simulated object-pose sample after the original
small-finger clearance hold, replans only its touch/close joints, and checks
knife/self/palm clearance before moving. All reference gates stay fixed.
It is a privileged planning diagnostic; geometric checks do not certify
physical holding. Read its actual report/failure before claiming capability.

Independent motor audit:
```bash
bash scripts/g2_local_python.sh -m scripts.audit_g2_hand_gravity \
  --run runs/g2-local-policy-20260928/R11-02-continuous-gravity-on-motor-feedforward \
  --output /tmp/my-g2-gravity-motor-audit.json
```

## Matched-state controls and single-inference S

The successful local S source is the actual H-prepared frame, not the earlier
pre-H state. This matched command keeps the original source, physics, clock and
motor limits. `learned-static` makes one network call and holds its normalized
20-joint output; the thumb geometric motor path continues with the clock.

```bash
bash scripts/g2_local_python.sh -m scripts.run_g2_local \
  --task S --baseline learned-static --num-envs 2 --episodes 1 \
  --state configs/g2_local/S-after-continuous-learned-H-state.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --video --output runs/g2-local-policy-20260928/my-matched-static-S
```

R13 matches `full-teacher`, `thumb-only`, `geometric-only`, and `learned-static`
on this same source. For `geometric-only`, add `--route joint --thumb-plan
configs/g2_local/thumb-material-path.json`. The zero residual keeps the joint
method's motor mapping and limits; this is not the different historical point
feedback controller. Exact commands and weights are also in each launch manifest.

The continuous prepared-state command above becomes R14's single-inference S
control by adding `--operation-static-policy` and choosing a new output. H stays
dynamic and privileged. The initial S observation is ideal simulated state;
subsequent S commands use clock, the geometric prior and their own last command.
This is not a trained student. The actual controller call count is recorded in
`report.json:operation_controller.actual_model_calls`; it must be one.

R12's separate fixed-H control removes `--learned-hold-policy` and adds
`--fixed-preparation-hold`. It retains actual motor targets for22s and the same
hold criteria. Both options are mutually exclusive. A failed preparation is a
whole-task failure even if later S were to pass. No pose/history is injected.

Independent read-only audits (fresh output names; no physical executions):

```bash
bash scripts/g2_local_python.sh -m scripts.audit_g2_prepared_continuous \
  --run runs/g2-local-policy-20260928/R12-03-seen00-fixed-preparation-hold \
  --launch runs/g2-local-policy-20260928/R12-03-seen00-fixed-preparation-hold-launch.json \
  --prefix-trace runs/g2-local-policy-20260928/R12-01-seen00-small-finger-landing/trace.npz \
  --prefix-until-phase fixed_motor_hold --source-prefix-until-phase learned_hold \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --output /tmp/my-seen00-fixed-H-audit.json

bash scripts/g2_local_python.sh -m scripts.audit_g2_prepared_continuous \
  --run runs/g2-local-policy-20260928/R14-01-continuous-initial-offset-S \
  --launch runs/g2-local-policy-20260928/R14-01-continuous-initial-offset-S-launch.json \
  --prefix-trace runs/g2-local-policy-20260928/R2-04-continuous-H-diagnostics/trace.npz \
  --checkpoint runs/g2-local-policy-20260928/B4-S-joint-path/checkpoint-00025.pth \
  --output /tmp/my-continuous-static-S-audit.json
```

The second command's prefix is the original full acquisition and H preparation.
The audit requires identical physical frames before the declared intervention;
for static S it additionally verifies one model call, constant normalized action
and replay of all600 actual commands. It does not relax any success threshold.


## Evidence restoration and browser playback

Extract the following Release archives into `runs/g2-local-policy-20260928`
in order; each is incremental and must not replace old results:

1. `g2-local-policy-baselines-evidence-20260928.tar.gz`
2. `g2-local-policy-joint-learning-R4-R6-increment-20260928.tar.gz`
3. `g2-local-policy-continuous-success-R7-increment-20260928.tar.gz`
4. `g2-local-policy-validation-input-R8-increment-20260928.tar.gz`
5. `g2-local-policy-support-gravity-R9-R13-increment-20260928.tar.gz`
6. `g2-local-policy-continuous-static-R14-final-increment-20260928.tar.gz`
7. `g2-local-policy-remaining-development-videos-increment-20260928.tar.gz`

Each archive has its own file-level SHA256 manifest and verified archive hash.
Source pins reuse the existing project's assets, Isaac Gym, caches and original
policy dependencies; this increment is not a duplicate of the earlier full
repository backup. The existing successful source pin remains unchanged.

The local browser page uses HTTP and includes WebM as a Firefox-compatible
fallback; avoid old absolute file URLs:

```bash
firefox http://127.0.0.1:8767/g2-local-policy-20260928/
```

The protected existing server serves
`/data/research/artgym-experiments-20260921/runs/wuji-goal/local-video-preview-20260924`.
On another machine, download named MP4/WebM assets from the Release and serve
the download directory with `python3 -m http.server 8767 --bind 127.0.0.1`.
Video files are uncut, original speed and contain no text overlays; page labels
state each run's actual scope and failure.
