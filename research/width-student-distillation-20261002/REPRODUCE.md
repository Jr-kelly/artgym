# Restore completed science and resume the frozen final

Endpoint17314 reconnected on2026-10-02T11:08UTC. The user supplied the provider notification: instance killed at10:10UTC after4h0m11s because four-hour GPU mean19.9461% was below26%. On reconnect all8H200 were idle and the temporary experiment directory was absent; the licensed runtime persisted. Authentication stays private.

Two paired optimization streams and all180dev/confirmation evaluations are complete. No training was restarted. Eight incomplete final jobs retain their original receipts and conservative1.4GPUh charge. The frozen90-task matrix resumes in `queues/frozen-final-resume-v2.json`, with retry1 names only for those8interrupted identities;82never-started tasks retain original names. Exact remote hashes match the original freeze. Final results are not used for model selection.

## Minimal restore

Clone the published branch `feat/wuji-width-student-distillation-20261002`. A licensed, configured IsaacGym/TacSL runtime is required and is not redistributed. The actual H200 runtime was Python3.8.20/PyTorch2.1.0+cu118, NumPy1.23.5, IsaacGym-TacSL, driver570.133.20. Existing runtime `/home/wangjiarui/artgym-runtime/bin/python` was reused. Import IsaacGym before Torch in physical commands; CPU-only checkpoint audits need no Gym import.

Restore `width-prepared-data-and-static-evidence-v1.tar.gz` from preserved preparation Release `wuji-width-student-distillation-20261002-preparation-v1`, SHAe5d3676ea821ab46ed532607c4c8f640fb8931ff5bc9184d4c69d63120c563ac. It contains new split states, assets, caches, accepted training/dev/unseen-static pools and sampler manifests. Restore `geometry-frozen-parent-models.tar.gz` from the old geometry Release, SHA5c5a1a91db8807473beccdc3f1f990036d4f5f036ef153b222e3c3825bb3e612; use only its two frozen parent files. Do not load any old final array.

From this research Release restore both `width-pair1-full-checkpoints-v1.tar.gz` and `width-pair2-full-checkpoints-v1.tar.gz`, plus `width-new-h200-static-and-video-states-v1.tar.gz`. The latter contains the accepted v2 H200seen confirmation/final pools; use STATIC_ACCEPTANCE_MANIFEST.json rather than historical incomplete static folders. Model/data packet receipts and the server digest index identify exact archives.

```bash
python3 -m scripts.restore_wuji_unified PACKET.tar.gz --output RESTORE_ROOT
```

This command checks every member SHA and refuses conflicting content. The critical firstpair models+H200states restore verified64files, actual mainC Adam54400/RNG and474W120final states; see CRITICAL_RESTORE_AUDIT.json. Additional large raw packets are optional for recomputing published results, not prerequisites for model inference.

Parents remain:

- Teacher `runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth`, SHA2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8.
- P `runs/unified-student-20261001/SA-real-51200/step_051200.pth`, SHA16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9.
- MainC `runs/width-student-distillation-20261002/C1-window1-h200-17314/step_054400.pth`, SHAb537578fc1123a6c3bad0358d8aa122b0c9c97bd970f98984960f685fa787a2f.

All six final model paths and all five cohort/asset/source hashes are immutable in final-freeze.json. Do not replace the mainC or G800 with a more favorable later model.

## Recompute completed statistics

Use the configured CPU environment with `PYTHONPATH=.:rl_games`, `CUDA_VISIBLE_DEVICES=''`, OMP/MKLthreads2. Restore the geometry-partitioned firstpair dev/confirmation and secondpair dev archives plus `width-completed-analysis-v1.tar.gz`.

```bash
python -m scripts.analyze_wuji_width \
  --manifest research/width-student-distillation-20261002/COMPLETE_CONFIRM_MANIFEST.json \
  --output NEW_CONFIRM_ANALYSIS
```

Other exact manifests are WINDOW1_COMPLETE_DEV_MANIFEST.json and REPEAT52000/52800/54400_DEV_MANIFEST.json. Each repeat checkpoint gets its own analysis: rolesC/G must not pool checkpoints. Source states are reused across models/protocols; bootstrap/Wilson episode intervals do not certify optimization-seed reproducibility. Analysis verifies source/model/cohort/selection/trace receipts and recalculates drift/rotation, phases, F cycles and S2/S5 strict endpoints.

```bash
python research/width-student-distillation-20261002/audit_full_checkpoints.py \
  --pair 1 --output NEW_PAIR1_AUDIT.json
```

Repeat withpair2 only if verifying restored copies. It reads actual Adam steps, moments, LR, frozen hashes, counters, RNG and geometry/source sampling; no GPU optimization or old recovery reruns.

## Reconciled interruption and frozen final

PROVIDER_KILL_RECONCILIATION.json and PRE_RECONCILIATION_RECEIPTS.json preserve the interruption evidence. `resume_after_kill.py` is the historical one-shot restoration controller, not an idempotent command to rerun. It restores exact sourceB/model/cohort files, preserves final_opened=true, then runs the versioned90-task queue. Check current STATE and live processes before any action. No further optimization, candidate reselection, threshold changes or batch/shard changes are allowed.

SourceA02749e10 exactly matches firstpair optimization; sourceBdba402c2 exactly matches secondpair and confirmation/final. The only A/B changes are the static constructor and queue mapping; trainer/task/controller/evaluator match. Frozen source SHA is a1739e7c66f61705b0b1d1edbf78c33924fb455d20471a9d35767afa38cd795e.

All final raw archives will be partitioned by geometry/protocol, preserving full original simulation batches, for publication in `wuji-width-student-distillation-20261002-final-v2`. Model, training/dev/confirmation and video assets remain in v1. Restore the15 `width-final-GEOMETRY-PROTOCOL-raw-v2.tar.gz` packets, then recompute with FINAL_MANIFEST.json:

```bash
python -m scripts.analyze_wuji_width \
  --manifest research/width-student-distillation-20261002/FINAL_MANIFEST.json \
  --output NEW_FINAL_ANALYSIS
```

The collector deduplicates registered identities;35280episode records represent1960initial states shared across6models×3protocols, not35280independent states. No incomplete killed trajectory is included.

A direct scientific evaluation example, after restoring the unchanged freeze and runtime:

```bash
CUDA_VISIBLE_DEVICES=0 python -m scripts.evaluate_wuji_geometry \
  --research-dir research/width-student-distillation-20261002 \
  --label W120 \
  --states runs/width-student-distillation-20261002/static/W120-final-v2/valid-states.npy \
  --model student --protocol F \
  --student-checkpoint runs/width-student-distillation-20261002/C1-window1-h200-17314/step_054400.pth \
  --output NEW_UNIQUE_FROZEN_FINAL_OUTPUT
```

For actual Goal execution use the finite launcher/receipts and account allocation rather than the unbounded shell example. JSONauthenticationargv is injected only privately as WUJI_WIDTH_SSH_ARGV. The checked-in dispatcher currently validates the user-authorized17314endpoint.

Once all90registered final identities finish, run collect_registered_queues.py with the reconciled versioned queue, independently rescore, update final_evaluation_complete=true, then make_research_figures.py --final and write_final_report.py. Do not invoke the latter while final is incomplete. Regenerate the exact resource table after receipt reconciliation. Restore/upload only new completed evidence assets; preserve all old Release assets. Publish final results without changing candidate selection or training.

## Historical training command (reproduction only, not an authorized restart)

Each formal job used the existing trainer, not a separate system:

```bash
python -m scripts.train_wuji_unified_student \
  --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth \
  --resume runs/unified-student-20261001/SA-real-51200/step_051200.pth \
  --output NEW_REPRODUCTION_DIRECTORY \
  --kind SC --controller-mode real --envs 256 --rollout-steps 4 \
  --width-arm C \
  --width-training-manifest research/width-student-distillation-20261002/data/C-training.json \
  --fresh-optimization-seed 2026100215 --seed 2026100215 \
  --updates 54400 --save-at 52000 52800 54400 \
  --lr .0003 --warm-updates 400 --target-loss-weight 25 --target-loss-scale .04
```

G changes only arm/manifest/output; seed2026100216 identifies the secondcleanparent pair. Own-checkpoint continuation omits freshseed and resets the simulator episode explicitly; it is not bitwise PhysX continuation. No main continuation beyond54400 occurred. No DDP/env×8/LR/loss/horizon change.
