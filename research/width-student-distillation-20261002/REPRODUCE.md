Current authorized port is17314 (user updated the connection after the documented33024 timeout). Existing remote runtime `/home/wangjiarui/artgym-runtime/bin/python` was verified and reused. Current source contract permits only the updated authorized endpoint. Set authentication privately as before. Same-H200 zero-change/disposable/fresh teacher checks passed; resume current active receipts, not a duplicate formal trial. Current parent/teacher dev queue is v7; v6 failed the missing constructor fallback dependency and is preserved.

# Resume the prepared width experiment

This is a prepared, unfinished experiment. H200 training and final policy evaluation have not run. The static preparation packet is separate from the prior closed geometry/student final datasets. Never substitute historical finals for new training or selection data.

Clone `feat/wuji-width-student-distillation-20261002`. Download `width-prepared-data-and-static-evidence-v1.tar.gz` from the independent preparation Release `wuji-width-student-distillation-20261002-preparation-v1` (SHA256 `e5d3676ea821ab46ed532607c4c8f640fb8931ff5bc9184d4c69d63120c563ac`). Restore it with `python3 -m scripts.restore_wuji_unified PACKET.tar.gz --output .`. Its161files were hash-verified in a fresh restore. The separate job-source-overrides archive preserves the exact versions that actually ran; reconstruct overrides over public base8968914 and verify its manifest. Reuse `geometry-frozen-parent-models.tar.gz` from the preserved [geometry Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-geometry-generalization-20261002-v1), SHA256 `5c5a1a91db8807473beccdc3f1f990036d4f5f036ef153b222e3c3825bb3e612`. The exact model hashes are in STATE and PARENT_AUDIT. Restore only required models; do not load old final arrays. Licensed IsaacGym/TacSL and a compatible configured runtime are not redistributed.

Authentication must remain in the operator's private environment. Set `WUJI_WIDTH_SSH_ARGV` to the JSON array for the provided SSH endpoint using existing authentication. Never add its value to Git, reports or stdout. The controller verifies the currently authorized username/endpoint/port and does not probe other hosts.

```bash
python3 -m scripts.inventory_wuji_width_remote \
  --output research/width-student-distillation-20261002/remote-inventory-restored.json
```

Read the returned remote AGENTS, active identities/executions, device inventory and runtime facts before launch. Reconcile changed cumulative cost or interrupted jobs first. If a new machine lacks the old runtime, restore only compatible required dependencies. Local scientific commands used Python3.8/PyTorch2.1+cu118/IsaacGym TacSL; a remote runtime is still unverified. Import IsaacGym before Torch. Transfer current `scripts`, `isaacgymenvs`, `rl_games`, assets/caches, this research directory and required `research/multigrasp-20260928/data/candidates.npy` into `/tmp/artgym-width-20261002/source`; include the unchanged baseline physics JSON under its old research path. Place frozen parents under `/tmp/artgym-width-20261002/runs` at their original relative paths. Source pins link to this shared runs directory. Do not overwrite an existing width workspace/job; inspect and resume it.

Prechecks are separate finite processes, each bound to an actually idle GPU. Launcher options precede the job name:

```bash
python3 -m scripts.wuji_width_jobs --gpu 0 --seconds 180 h200-C-input \
  -- PYTHON -m scripts.precheck_wuji_width_environment --backend H200 --arm C \
  --actor-parity --output runs/width-student-distillation-20261002/precheck/h200-C
```

Run corresponding G input check on another idle H200. Check zero-change C versus the original baseline path with identical registered reset states/public inputs. Use only fresh dev for tiny baseline/W120 teacher from-reset behavior checks. Neither local input checks nor historical two-second interventions satisfy these actual H200 prechecks.

For each arm use a disposable clean-parent training process with endpoint51216, save51216 and fresh optimization seed2026100215. This performs16 real Adam updates/16384 transitions. Verify only the student changed, actor/teacher/normalizers remained frozen, teacher fraction0, executed-target/RNN assertions passed, restored Adam parameters were correct, and optimizer/RNG can resume the discarded copy. The disposable file is never a formal starting candidate. Measure complete loop wall time from learning/complete receipts, including teacher labels, physics and backward; separately account initialization/save/launcher allocation. Register the first matched-window endpoint/timeout and costs before starting formal training. Reduce both arms equally only if measured costs cannot fit both arms, dev and6GPUh reserve.

Formal C and G both reload untouched SA51200. Each has its own output directory. Example C (G changes `--width-arm`, manifest and output only):

```bash
python3 -m scripts.wuji_width_jobs --gpu 0 --seconds REGISTERED_TIMEOUT C1-window1 \
  -- PYTHON -m scripts.train_wuji_unified_student \
  --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth \
  --resume runs/unified-student-20261001/SA-real-51200/step_051200.pth \
  --output runs/width-student-distillation-20261002/C1-window1 \
  --kind SC --controller-mode real --envs 256 --rollout-steps 4 \
  --width-arm C \
  --width-training-manifest research/width-student-distillation-20261002/data/C-training.json \
  --fresh-optimization-seed 2026100215 --seed 2026100215 \
  --updates 54400 --save-at 52000 52800 54400 \
  --lr .0003 --warm-updates 400 --target-loss-weight 25 --target-loss-scale .04
```

For an authorized later window resume each arm's own atomic checkpoint, use a new output/job directory and **omit** `--fresh-optimization-seed`. Restore its own sampler counters/RNG, absolute step and Adam. Episode reset is explicit; no PhysX bitwise continuation claim. Never pass `--updates 3200` as an added budget.

The finite dev queue builder validates atomic published checkpoint hashes and fixed cohort/batch identities. Rebuild a new queue version if source changes before launch; retain previous versions as unexecuted records. Prior prepared queues can contain an earlier source digest and must not be run unchanged after code edits.

```bash
python3 -m scripts.wuji_width_queue build --phase dev \
  --models P=runs/unified-student-20261001/SA-real-51200/step_051200.pth \
    teacher=runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth \
  --output research/width-student-distillation-20261002/queues/dev-current-source.json
python3 -m scripts.wuji_width_queue run \
  --queue research/width-student-distillation-20261002/queues/dev-current-source.json \
  --gpus VERIFIED_IDLE_GPU_INDICES
```

Run C/G training on two devices and P/teacher/checkpoint dev on the remaining verified idle devices, up to8 total including local rendering. GPU numbering is logical until inventory. No DDP/env expansion; no user-job preemption. Queue completion does not authorize crossing a training-window boundary: apply GOAL section6 behavioral and budget rules first. Prioritize W120source3 F joint success, baseline preservation and widthsource2 regression; assess adjacent saved checkpoints. Do not use loss as behavior evidence.

After selecting on new dev/eligible confirmation, write `final-freeze.json` with registered `state_sha256` and `model_sha256` lists, chosen G and equal-update C, teacher/P, selection rule and immutable source/asset/plan hashes. Opening final before this fails the evaluator guard. The final matrix and counts must also be frozen before policy access. Retain one final opening; do not choose another model or repair data afterward.

`analyze_wuji_width --manifest RUN_MANIFEST --output NEW_ANALYSIS` independently reuses the original trace scorer, validates each model/cohort/selection/trace SHA and duplicate identities, computes functional/holding/joint Wilson intervals and paired four cells, and splits F first/last20seconds. Its required run manifest supplies `teacher_sha256`, `historical_final_access:false`, and each completed run's directory, selection path/SHA, model role/SHA, geometry, protocol, state SHA and trace SHA. Do not create a success report for an empty queue. Rows of multiple protocols/checkpoints are correlated episodes, not new independent initial states.

Videos remain pending until actual C/G candidates exist. Use first accepted new-dev source3 states for baseline/W120, same initial state for P/C/G/teacher, retain failures and label all results. RTX4090 videos are separate rendered resimulations, never H200 statistics or hardware validation. Reuse the existing renderer/package/temporal reset-step interface; preserve known H200-to-CPU parity limitations.

All own jobs have timeout, immutable pin, source/model/asset/cohort identities and start/end GPU allocation receipts. New executions save surviving runner/child PID receipts. Lost SSH transport sets unknown status and conservatively reserves the whole timeout; reconcile actual remote receipt before more launches. No owned process or monitor is currently active. ToDesk and unrelated jobs remain intact.

Local follow-up evidence is additive: `width-local-precheck-and-disposable-updates-v1.tar.gz` restores only the new fixed-state traces, four discarded checkpoints, six job receipts and immutable audits. It has the standard release-manifest format and must pass the same restore command in a fresh directory. `width-local-precheck-job-source-overrides-v1.tar.gz` separately preserves the exact source pins for these six jobs; its receipt is SOURCE_PINS_LOCAL_PRECHECK.json. It does not replace the original preparation packet/source-pins archive. Discarded checkpoints are not research candidates.

Zero-change precheck: generate a new fixed fixture with `precheck_wuji_width_zero_change fixture --output NEW_FIXTURE`; launch `capture --path original` and `capture --path multiasset` in **separate** finite processes, passing identical `--fixture`, `--backend H200`, and distinct `--output` paths. Invoke `compare --original ORIGINAL_OUTPUT --multiasset MULTIASSET_OUTPUT --output NEW_AUDIT`. Bind each capture to a verified idle H200 through the launcher. The published RTX fixture is256 fresh accepted baseline training states; do not substitute oldfinal states. A4090 numerical pass does not replace this H200 check.

The local launcher permits only explicitly bounded `--local --disposable-precheck` width optimizer checks, endpoint51216 from the common parent/fresh seed2026100215, or51217 from its own discarded51216 checkpoint without a fresh seed. Formal local optimization remains disabled. The actual local checks passed34 updates and own-checkpoint resume. Avoid repeating them onRTX; measure H200 full-loop throughput in the required same-backend precheck before registering the formal budget. Four discarded weights must never enter a formal dev/final queue or become a training starting point.

Current prepared finite queue is `queues/parent-teacher-dev-source-v5.json`; v1-v4 are retained unexecuted and have earlier source digests. Source changes require a new version. All currently owned jobs have finished; recheck live receipts and allocation independently on the remote before assuming idle GPUs.

Follow-up packet SHA256: `0ed35dc8798ecfa21c67055ff6397e305bd6e5128db0e7dfd00e8a5ee2b32b3f` (71files). Follow-up source-pins archive SHA256: `ff7e6693a2bf4a93cd296bdd965f4779ad7433735142c7636b908853d93780f5`. Server digests were verified; original two preparation assets remain unchanged.
