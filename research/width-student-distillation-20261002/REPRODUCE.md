# Restore completed science and resume the frozen final

Current authorized endpoint `ssh -p 17314 wangjiarui@10.13.160.5` connected and ran the two paired experiments, but all eight final SSH sessions closed at about2026-10-02T10:10UTC; a10:12:42UTC reconnect timed out before authentication. This endpoint is currently unavailable. Authentication stays in the operator's private environment. Do not probe historical ports or serialize private SSH arguments.

Two optimization streams are complete: C1/G1 seed2026100215 and C2/G2 seed2026100216, each arm51200→54400, saving52000/52800/54400,12,800total updates. All126dev and54confirmation runs are independently rescored. Final is **opened, frozen and unfinished**:8unknown execution receipts,82pending tasks,0counted final runs. The native Goal is not complete. Never rerun training or choose models based on a final retry.

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

## Recover the interrupted final without duplicating work

First recover the authorized endpoint or receive a new explicitly authorized endpoint. Re-inventory live GPUs/runtime/user tasks. Check the8names in STATE.unreconciled_remote_jobs and their surviving remote `runs/width-student-distillation-20261002/jobs/NAME/execution.json` receipts. A transport failure is not evidence the child stopped. Each has a finite600s timeout plus30s termination grace. The current ledger charges1.4GPUh across8unknown jobs pending reconciliation; never erase those charges just because SSH failed.

If a job really finished, retrieve its exact output/receipt, verify frozen hashes and only then mark its queue task complete. If it terminated incompletely, preserve old output/identity/log and register a bounded retry in a new output directory with the identical scientific identity, model, cohort, batch size, source assets and protocol. Count exactly one completed result per scientific identity. Do not simply reset all90tasks to pending or overwrite old results. Preserve final_opened=true and final-freeze.json byte-for-byte.

If the instance and/tmp are gone, restore prepared files/parents/checkpoints/assets/caches into a new independent source/runs staging layout. SourceA02749e10 exactly matches firstpair optimization; sourceBdba402c2 exactly matches secondpair and confirmation/final, and differs only in staticconstructor and queue mapping. All actual training/task/controller/evaluator files match. Recreate the exact sourceB for final. Any necessary new-endpoint launcher routing change must be documented separately without changing scientific inference files or frozen model/data/thresholds. Do not reuse discarded precheck checkpoints.

Only launch on verified idle H200 devices, atmost8GPUs acrossallmachines. No further training is allowed now final is open. Completed12videos require no new GPUrender. Use surviving complete tasks and claim only still-missing identities from a newly versioned finite queue. Read current STATE and receipts before launching; remaining budget is conservatively13.10091779GPUh pending those8receipts, original cumulativecap64unchanged. Use finite timeouts based on actual512batch throughput, with no batch/shard change after final opening.

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
