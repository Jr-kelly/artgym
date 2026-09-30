# Restore and reproduce

Use this experiment's branch `feat/wuji-artmanip-recovery-20260930`. The release tag is `wuji-artmanip-recovery-20260930-v1`; training and the once-only final evaluation are complete. Each tar archive includes per-file SHA256 values. Download the assets into a separate checkout and restore with:

```bash
python3 -m scripts.restore_wuji_unified recovery-assets-resets.tar.gz --output .
python3 -m scripts.restore_wuji_unified recovery-expert-parents.tar.gz --output .
python3 -m scripts.restore_wuji_unified recovery-training-sequences-t2.tar.gz --output .
python3 -m scripts.restore_wuji_unified recovery-training-sequences-t5.tar.gz --output .
python3 -m scripts.restore_wuji_unified recovery-reference-pilot20.tar.gz --output .
```

Other completed-stage archives use the same restorer. It refuses conflicting existing files. Large weights and physical traces live in Release assets. Source/config/report files live in Git; immutable source SHAs and complete commands are in `jobs/*.json`, and checkpoint/data SHAs in the corresponding manifests. The supplied remote launcher is specific to this session's authorized host; an address in a historical receipt is not permission to use that host.

A compatible IsaacGym TacSL installation, Python3.8, PyTorch2.1.0+cu118 and NVIDIA driver are needed. The tested runtime was relocated from an existing environment, including its IsaacGym editable-install paths. Do not assume a copied `.egg-link` still points to a valid package. On an authorized device, adapt the runtime prefix consistently:

```bash
export WUJI_PYTHON=/path/to/artgym-runtime/bin/python
export LD_LIBRARY_PATH=/path/to/artgym-runtime/lib:$LD_LIBRARY_PATH
export PYTHONPATH="$PWD:$PWD/rl_games"
export PYTHONNOUSERSITE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MAX_JOBS=2
export CUDA_VISIBLE_DEVICES=0
```

System `python3` is sufficient for archive/JSON orchestration. Use the runtime interpreter for NumPy, Torch and simulator scripts. Keep assets as actual files under the checkout: IsaacGym did not resolve a source-pin asset symlink escaping its root. This round uses immutable source snapshots and hard-linked asset copies without modifying their source assets.

## Joint RL

The reference starts from random seed2026093011, with no old mixed-action expert initialization. Pilot20 is 1,638,400 environment interactions and720 actual Adam updates. Its `initial.pth` is the random starting state; its `checkpoints/epoch_000020.pth` is a genuine resumable learner. Actual epoch20→21 restoration was verified, with Adam720→756 and full model/normalizer/RNG restored. PhysX is not serialized: every resumed run starts new physical rollouts and reset recurrent histories. Do not claim bitwise equivalence to uninterrupted simulation.

The first formal segment continues the pilot to cumulative epoch1000:

```bash
"$WUJI_PYTHON" -m scripts.train_wuji_recovery_rl \
 task=wuji_artmanip_reference hand=wuji_paper_official_actuator \
 object=knife_wuji_reference train=wujiArtManipReferenceSAPG \
 num_envs=5120 headless=True pipeline=gpu graphics_device_id=-1 \
 force_render=False num_subscenes=0 multi_gpu=False seed=2026093011 \
 experiment=my-reference-segment1 max_iterations=1000 \
 checkpoint=runs/recovery-rl-pilot20-retry2/checkpoints/epoch_000020.pth \
 train.params.config.save_frequency=250 \
 train.params.config.evaluation_frequency=250 \
 train.params.config.checkpoint_first_epoch=250
```

Use new output names. Subsequent segments resume the corresponding previous1000/2000/3000 checkpoint and end at2000/3000/4000. The preregistered baseline is327,680,000 interactions, not the paper's2B category-level experiment. Actual per-epoch optimizer counts, source visits/interactions, rewards and curriculum weights are in `learning.jsonl`; `resolved.yaml`, `resolved-learner.json`, and actual constructed environment `startup.json` distinguish configuration from runtime behavior. Five SAPG blocks and coefficient50 inference remain fixed.

## Paired recurrent BC

The historical BC100 starting SHA is `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`. Both arms restore its actual800-step Adam/RNG. M supervises original expert μ; E supervises `clip(expert μ,-1,1)` using the unbounded network output in the loss. Both keep old mixed control, whole600-step episodes, actual previous executed action, shifted done masks, fixed normalization and their own jointly trained encoder/actor. Source/phase sampling and LR are identical.

```bash
"$WUJI_PYTHON" -m scripts.run_wuji_recovery_bc_pair \
 --name my-bc-added800 --previous-epoch 100 --end-epoch 200 --max-seconds 1400
```

For later segments pass `--previous-name my-bc-added800 --previous-epoch 200 --end-epoch 300` and a new name; then300→500 and500→900 give cumulative added1600,3200,6400 updates. Optional900→1700 requires ongoing evidence and remaining budget. The driver serially executes both arms on the assigned GPU. `training.jsonl` stores actual changing-model training batches; `metrics.jsonl` stores frozen validation and first-eight fitting-trajectory probes. Do not confuse either with closed-loop success.

## Independent physical protocols

A single model instance controls all four source groups in each batch. Prefix an incremental-reference model name with `rl`; other model names select the historical mixed interface. No source routing occurs within a model. This example evaluates BC800 outcomes:

```bash
"$WUJI_PYTHON" -m scripts.evaluate_wuji_recovery_batch \
 --name my-bc800-development \
 --states research/artmanip-recovery-20260930/data/development-all.npy \
 --models M200=runs/artmanip-recovery-20260930/bc-pair800/M/epoch_000200.pth \
          E200=runs/artmanip-recovery-20260930/bc-pair800/E/epoch_000200.pth \
 --protocols S2 S5 F
"$WUJI_PYTHON" -m scripts.summarize_wuji_recovery \
 --directories runs/artmanip-recovery-20260930/my-bc800-development \
 --output research/artmanip-recovery-20260930/my-bc800-analysis
```

F has a40-second maximum horizon,10mm tolerance, and1.5 seconds continuously at target before switching. A complete open-close cycle counts as functional success; full survival/body stability and later drops are reported separately. If all environments terminate early, the physical trace ends there and records failure/survival facts; it does not pretend to contain40 seconds of live behavior.

S is a separate20-second episode with external2/5-second switching. Every stage's final9 control samples must stay within2mm, with full validity/survival and base drift<10mm/rotation<.25rad. The original and independent strict scorers agree episode by episode. F's state machine is reconstructed independently from its own physical trace. Development/promotion are separate from the new final128/source set. Do not open final trajectories/scores during training or selection.


## Matched holding-objective comparison after static reset repair

The original4segment reference retains its original training pool, whose complete512-row static diagnostic found4 unstable source0 perturbations. Those facts are retained in its interpretation. The later controlled comparison uses a separate repaired training-only pool for **both** arms, with explicit4-row mapping and SHA in`data/rl-train-static-valid.json`. All development/promotion/final states remain unfiltered. The full repaired512-row20s static/clock check passed; this is initialization evidence, not policy success.

Resume the originalRL1000 checkpoint with the jointRL command above, using `max_iterations=2000`, `train.params.config.checkpoint_first_epoch=1250`, and `task.env.trainingStates=research/artmanip-recovery-20260930/data/rl-train-static-valid.npy`. Use separate experiment names. Select `task=wuji_artmanip_reference` for the matched original-goal control and `task=wuji_artmanip_clock_hold` for the fixed-clock/sustained-body objective. Both receive81,920,000 additional environment interactions and36,000 actual Adam updates from the same parent optimizer/RNG. Evaluate both with names beginning `rl`, which selects their full-incremental physical control interface. Compare both to the separately retained original-pool baseline.

CPU checkpoint and actual resumed-first-update verification:

```bash
"$WUJI_PYTHON" -m scripts.audit_wuji_recovery_rl \
 --checkpoint runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth \
 --epoch 1000 --resumed-run runs/recovery-rl-clockhold-clean \
 --output holding-resume-audit.json
```

The simulation precheck scripts require explicit global RNG seeding for random sampling; `isaacgymenvs.make(seed=...)` alone does not seed Torch/NumPy. Formal RL already calls the upstream `set_seed`; full-pool diagnostics enumerate exact rows and also set global seed. Recorded evaluations load fixed state matrices and report physical trace hashes.


Evaluation players call `Runner.load_config`, which seeds Torch/CUDA/NumPy/Python; actual evaluation logs show `self.seed = 2026093031`. The standalone precheck seeding issue therefore does not imply unseeded policy evaluations. Another configuration distinction is explicit: reference YAML contains `jointNoise=.01`, but `ArtManip.__init__` forces `joint_noise=0` and `force_scale=0` when `task.randomize=false`, as in every current reference startup configuration. New startup/evaluation reports record these effective instance attributes; historical source pins and configurations establish the same constructor path. Existing training physics/observations are not changed by this logging addition.


For final physical evaluation only, `scripts.launch_wuji_recovery --final` requires an exact committed `final-freeze.json` with `source_sha` identifying frozen simulator/evaluator code. It rejects training commands and requires all development/training jobs to finish. Normal jobs subtract the current reserved-final GPU budget in STATE.json from the24GPUh limit and honor its training cutoff. After the exactS64 pass, the registered full second-seed replication reallocated0.5GPUh: the current reserve is3.5GPUh and2wall hours (20.5GPUh/20:42UTC ordinary ceiling); frozen final jobs may use up to24GPUh and22:42UTC. Earlier development reserved4GPUh; see teacher-method-freeze.json and STATE.json for the dated allocation. This switch does not authorize repeated tuning or reopening final scores. Development ended before the final cohort was first transferred; the frozen18-model validation started at18:19UTC. No further training or reselection is allowed.


Final model selection is reproducible with `scripts.freeze_wuji_recovery`: supply all completed development `--gates`, at least one `--endpoints` name per trained family (include both E4100 matched-budget and E5700 extended endpoints), and the evidence/budget `--reason` for ending development. It requires the originalRL4000 development result and the repaired-pool original control, rechecks no active GPU jobs, ranks each family using the preregistered ordering, retains fixed endpoints and the BC100/RL1000 anchors, resolves exact weights through actual batch plans, and hashes the untouched final state file. It creates `final-freeze.json` exclusively and records the event; it does not evaluate. Commit that exact file before using the final launcher. The helper produced the once-only freeze at18:18UTC, committed before final cohort transfer and evaluation. Do not run it again for this round.


TheBC32000 complete local archive exceeded GitHub's2GiB single-asset limit. Published `recovery-bc32000-M.tar.gz` and `recovery-bc32000-E.tar.gz` restore into the same output root and together reconstruct the complete run. The oversized full archive remains in local `delivery/artmanip-recovery-20260930/local-only/`. `audit_wuji_recovery_bc --parent-pair runs/artmanip-recovery-20260930/bc-pair19200 --parent-epoch 2500` additionally checks the new segment's actual saved initial model, full Adam and CPU/CUDA/NumPy RNG against each parent, plus the first new update.


## Training-state aggregation availability pilot

`aggregation1-plan.json` fixes the prospective gate before collecting data. `prepare_wuji_recovery_aggregation initials` selects24 fitting and8 heldout initial states per source from the existing BC training split, preserving original whole-trajectory separation. `run_wuji_recovery_aggregation_collection` runs behavior and scripted early-handover episodes for2/5 seconds. Each responsible expert keeps its own normalizer and recurrent state from the same reset, receives actual previous behavior actions, and resets at actual done. A same-GPU full-history replay must reproduce labels within1e-5. CPU versus historical GPU replay did not meet1e-4; that discrepancy remains a diagnostic, not a passed check.

`assess_wuji_recovery_aggregation` independently scores handover availability. It requires body retention in all cells, old-source strict retention, and improvement of source3S5 holding or strict success. No new-data fitting is allowed without this result. If allowed and budget permits, `prepare_wuji_recovery_aggregation mix` retains all96 old fitting histories and adds24 new histories or24 repeated old histories; both arms share40 heldout histories. `run_wuji_recovery_aggregation_pair` restores the same E5700 model/Adam/RNG and gives both arms6400 additional updates with batch120 and LR1e-5. This is a separate controlled extra-data pilot; M/E matched-budget claims end at32000.


## Prospective second optimization seed and final replication endpoint

After the exact same-cohort64 S gate passes, the conditional plan may repeat the full selected E44800 plus aggregation3200 route from BC100 with `--resume --sequence-seed 2026093061`. This explicitly preserves parent model/Adam while resetting CPU/CUDA/NumPy optimization sampling state after restoration. The default absent flag preserves previous RNG continuation behavior. `audit_wuji_recovery_seed_fork` checks the actual saved pre-update model/Adam, new generator states and first update. This is a second optimization seed with shared experts and shared BC100 initialization, not independent expert pretraining. The full second optimization seed was launched at17:12UTC after the exact64 S gate passed; current execution status is in STATE.json.

If completed, pass the predeclared second-seed endpoint to `freeze_wuji_recovery --replicates seed2Eagg6100`. Replication endpoints receive full frozen final evaluation and retain their fixed weights, but do not compete with primary family candidates for checkpoint choice or video selection. Keep the original32-ranked Eagg6100 selection; its independent64 gate is verification evidence, not a replacement32 assessment fed into duplicate-candidate merging.


After frozen local videos are rendered, package with `package_wuji_recovery_video`. Direct MP4 Release receipts use `kind: standalone_video`, relative `archive` path, exact `sha256` and byte `size`; `upload_wuji_recovery` verifies the same GitHub server digest as for tar archives. The weight index hashes these standalone videos separately and does not treat them as checkpoint tarballs. Video trace/report/config sources remain in a normal verified evidence archive.

After all frozen final batches complete, rescore their original traces with
`summarize_wuji_recovery`, then run the complete-cohort audit:

```bash
python3 -m scripts.audit_wuji_recovery_final \
 --analysis research/artmanip-recovery-20260930/final-analysis \
 --output research/artmanip-recovery-20260930/final-integrity.json
```

The audit requires every frozen model/protocol exactly once,512 unfiltered initial rows,
matching weight/cohort/evaluator/scorer hashes, the declared control interface and protocol,
and128 unique independently scored trials per source. It checks completeness and provenance;
capability is assessed separately by `gate_wuji_recovery` using final same-cohort experts.

The local renderer rechecks compute processes and free memory immediately before launch.
On this workstation, ToDesk's verified `--isVideoSession=true` desktop session appears as
C+G in `nvidia-smi`; it is preserved and recorded. Only that exact desktop process is allowed
alongside video rendering, with at least16GiB free. Any unknown compute process blocks launch.
Local video starts only after remote jobs finish and is included in the same occupied-GPU ledger.

## Offline verification of the published final comparison

The final artifact set uses one `recovery-final-MODEL.tar.gz` per frozen model,
`recovery-final-weights.tar.gz` for all18 frozen checkpoint files plus the joint-limit
reference, and `recovery-final-batch-records.tar.gz` for completed batch records.
Download all `recovery-final-*.tar.gz` assets from this round's public Release into a
separate checkout of the published branch/tag, then restore:

```bash
for wuji_archive in recovery-final-*.tar.gz; do
  python3 -m scripts.restore_wuji_unified "$wuji_archive" --output .
done
CUDA_VISIBLE_DEVICES='' "$WUJI_PYTHON" -m scripts.summarize_wuji_recovery \
 --directories runs/artmanip-recovery-20260930/final-g0 \
               runs/artmanip-recovery-20260930/final-g1 \
 --output my-final-analysis
python3 -m scripts.audit_wuji_recovery_final \
 --analysis my-final-analysis --output my-final-integrity.json
python3 -m scripts.gate_wuji_recovery \
 --reports my-final-analysis/report.json \
 --experts my-final-analysis/report.json --output my-final-gates.json
```

This verifies recorded final trajectories without starting IsaacGym or using a GPU.
The final weights bundle is necessary for the completeness auditor's exact checkpoint
hash checks; the per-model final archives contain physical traces and resolved configs.
New physical simulation additionally requires the asset/runtime installation described
above and is a separate reproduction, not a replacement for the once-only results.

Within the original experiment session, the primary model was independently scored early
from its restored archive. `complete_wuji_recovery_final_analysis` reuses that cached result
and scores the remaining17 restored models, preserving the same scorer hash, before
merging `final-analysis`. It is a session orchestration helper with resource checks; the
commands above are the portable offline rescore procedure.


## Exact commands and source snapshots used in this round

The commands above are explanatory examples. The following immutable job specifications
contain the actual argument arrays, parent checkpoints, source commit, timeout and device
allocation. Their wrapper directories in the corresponding Release archives contain
`status.json` and `output.log`; training directories additionally contain the parsed
configuration and resume metadata. Restore each parent before attempting a continuation,
use the specification's source commit, and choose a fresh output name for a new run.
These are reproducibility records, not instructions to repeat this round's opened final set.

|Stage|Actual job specification|
|---|---|
|Original joint RL, segments 1–4|[1](jobs/rl-seg1-retry1-job.json), [2](jobs/rl-seg2-job.json), [3](jobs/rl-seg3-job.json), [4](jobs/rl-seg4-job.json)|
|Matched M/E, cumulative 32,000 added updates|[M/E final segment](jobs/bc-pair32000-job.json); preceding segments are indexed in [jobs](jobs)|
|E extension to 44,800 added updates|[E extension](jobs/bc-executed44800-job.json)|
|Same-parent original-goal and holding-goal RL controls|[Original goal](jobs/rl-reference-clean-job.json), [holding goal](jobs/rl-clockhold-clean-job.json)|
|Own-history collection and matched aggregate/replay fitting|[Collection](jobs/aggregation1-collection-job.json), [paired fitting](jobs/aggregation1-pair6400-job.json)|
|Primary independent 64/source confirmation|[Confirmation](jobs/aggregation1-promotion64-job.json)|
|Second optimization seed, complete route|[E 44,800](jobs/bc-seed2-executed44800-job.json), [own collection](jobs/aggregation2-collection-job.json), [aggregate 3,200](jobs/bc-seed2-aggregate3200-job.json)|
|Second-seed independent 64/source confirmation|[Confirmation](jobs/seed2-promotion64-job.json)|
|Once-only frozen final comparison|[GPU 0](jobs/final-g0-job.json), [GPU 1](jobs/final-g1-job.json), [immutable freeze](final-freeze.json)|

The primary's aggregate 6,100 checkpoint contains48,800 total BC Adam updates:
800 inherited at BC100,44,800 execution-label updates, then3,200 aggregation updates.
Its6,500 fixed endpoint and the replay6,500 control contain52,000 total updates.
Both matched M/E4,100 checkpoints contain32,800 total updates. Epoch numbers are
serialized continuation labels; they are not environment interactions or optimizer counts.


## Completed inventory and public verification

`weights-coverage-final.json` checks all scoped local PTH contents. `weights-aliases-final.json` maps11 `latest`/`best` or duplicate pilot filenames to already archived identical hashes. Restore the canonical numbered paths used by the job specifications; aliases contain no extra learned state. `recovery-historical-and-pilot-extra-weights.tar.gz` retains the two inherited earlier BC snapshots and auxiliary pilot inference snapshot found by this coverage audit. Weight file counts include duplicate content and do not mean independent trained policies.

After publication, `scripts.verify_wuji_recovery_public --output MY_RECEIPT.json --download-root NEW_EMPTY_DIRECTORY` runs under the CPU scientific interpreter. It queries the public Release without authentication, checks every asset name/size/server digest, anonymously downloads the primary69MB archive and all3 labelled MP4s, actually restores and CPU-loads the primary model/Adam/RNG, and decodes/checks each video's full frame count and duration. It does not run simulation. Publication receipts are committed after the scientific release tag because they can only be produced once the assets are public.

The final session rescore helper uses system Python with `LD_LIBRARY_PATH` cleared for SSH/resource orchestration; its scientific scoring subprocess keeps the runtime environment. This prevents the observed system-SSH/Conda-OpenSSL conflict without changing frozen simulator or scoring code.
