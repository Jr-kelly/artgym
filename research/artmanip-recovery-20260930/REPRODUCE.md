# Restore and reproduce

Use this experiment's branch `feat/wuji-artmanip-recovery-20260930`. The release tag is `wuji-artmanip-recovery-20260930-v1`; while training is active it is a draft. Each tar archive includes per-file SHA256 values. Download the assets into a separate checkout and restore with:

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


For final physical evaluation only, `scripts.launch_wuji_recovery --final` requires an exact committed `final-freeze.json` with `source_sha` identifying frozen simulator/evaluator code. It rejects training commands and requires all development/training jobs to finish. Normal jobs subtract the current reserved-final GPU budget in STATE.json from the24GPUh limit and honor its training cutoff. The expanded comparison now reserves4GPUh and2wall hours (20GPUh/20:42UTC ordinary ceiling); frozen final jobs may use up to24GPUh and22:42UTC. This switch does not authorize repeated tuning or reopening final scores. The final cohort has not been opened during current development.


Final model selection is reproducible with `scripts.freeze_wuji_recovery`: supply all completed development `--gates`, one `--endpoints` name per trained family, and the evidence/budget `--reason` for ending development. It requires the originalRL4000 development result and the repaired-pool original control, rechecks no active GPU jobs, ranks each family using the preregistered ordering, retains fixed endpoints and the BC100/RL1000 anchors, resolves exact weights through actual batch plans, and hashes the untouched final state file. It creates `final-freeze.json` exclusively and records the event; it does not evaluate. Commit that exact file before using the final launcher. This helper has been syntax/rank checked on existing development evidence; it has not been run to freeze the current experiment.


TheBC32000 complete local archive exceeded GitHub's2GiB single-asset limit. Published `recovery-bc32000-M.tar.gz` and `recovery-bc32000-E.tar.gz` restore into the same output root and together reconstruct the complete run. The oversized full archive remains in local `delivery/artmanip-recovery-20260930/local-only/`. `audit_wuji_recovery_bc --parent-pair runs/artmanip-recovery-20260930/bc-pair19200 --parent-epoch 2500` additionally checks the new segment's actual saved initial model, full Adam and CPU/CUDA/NumPy RNG against each parent, plus the first new update.


## Training-state aggregation availability pilot

`aggregation1-plan.json` fixes the prospective gate before collecting data. `prepare_wuji_recovery_aggregation initials` selects24 fitting and8 heldout initial states per source from the existing BC training split, preserving original whole-trajectory separation. `run_wuji_recovery_aggregation_collection` runs behavior and scripted early-handover episodes for2/5 seconds. Each responsible expert keeps its own normalizer and recurrent state from the same reset, receives actual previous behavior actions, and resets at actual done. A same-GPU full-history replay must reproduce labels within1e-5. CPU versus historical GPU replay did not meet1e-4; that discrepancy remains a diagnostic, not a passed check.

`assess_wuji_recovery_aggregation` independently scores handover availability. It requires body retention in all cells, old-source strict retention, and improvement of source3S5 holding or strict success. No new-data fitting is allowed without this result. If allowed and budget permits, `prepare_wuji_recovery_aggregation mix` retains all96 old fitting histories and adds24 new histories or24 repeated old histories; both arms share40 heldout histories. `run_wuji_recovery_aggregation_pair` restores the same E5700 model/Adam/RNG and gives both arms6400 additional updates with batch120 and LR1e-5. This is a separate controlled extra-data pilot; M/E matched-budget claims end at32000.
