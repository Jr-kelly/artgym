# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T20:04:28.331650+00:00",
  "event": "final_branch_delivery_verified_round_closed",
  "receipt": {
    "utc": "2026-09-30T20:04:28.323850+00:00",
    "verified_delivery_commit": "4944b9c4462ce9517e3bb370f2a9c435b4e88f4c",
    "remote_branch_commit": "4944b9c4462ce9517e3bb370f2a9c435b4e88f4c",
    "worktree_clean_at_check": true,
    "public_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-artmanip-recovery-20260930-v1",
    "assets": 86,
    "release_body_matches_committed_notes": true,
    "scope": "Final scientific and public recovery evidence is committed and pushed; subsequent journal-only commit preserves this verification without changing experiments or assets."
  },
  "evidence": "research/artmanip-recovery-20260930/branch-delivery-verified.json",
  "next": "This bounded round is complete; no active experiments, uploads or monitors. Preserve finalcohort and primary. Only next research priority is separately registered unifiedteacher-to-student distillation with verified available observations and new validation states."
}
```

预算与任务状态：
```json
{
  "start_utc": "2026-09-30T06:42:33+00:00",
  "deadline_utc": "2026-09-30T22:42:33+00:00",
  "training_cutoff_utc": "2026-09-30T20:42:33+00:00",
  "max_gpu_hours": 24,
  "reserved_final_gpu_hours": 3.5,
  "max_concurrent_gpus": 2,
  "rl_default_gpu_hours": 16,
  "bc_default_gpu_hours": 2.25,
  "phase": "Bounded experiment complete: primary andsecondseed finalS passed,86assets public/downloadrestored,ownedprocesses stopped",
  "active_jobs": [],
  "gpu_hours": 22.417678576666656,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Next round: distill this single frozen privileged teacher into a student using verified available observations/history, freeze actor, and evaluate on newly preregistered states. No more training or final-set tuning in this round.",
  "last_event": {
    "utc": "2026-09-30T20:04:28.331650+00:00",
    "event": "final_branch_delivery_verified_round_closed",
    "receipt": {
      "utc": "2026-09-30T20:04:28.323850+00:00",
      "verified_delivery_commit": "4944b9c4462ce9517e3bb370f2a9c435b4e88f4c",
      "remote_branch_commit": "4944b9c4462ce9517e3bb370f2a9c435b4e88f4c",
      "worktree_clean_at_check": true,
      "public_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-artmanip-recovery-20260930-v1",
      "assets": 86,
      "release_body_matches_committed_notes": true,
      "scope": "Final scientific and public recovery evidence is committed and pushed; subsequent journal-only commit preserves this verification without changing experiments or assets."
    },
    "evidence": "research/artmanip-recovery-20260930/branch-delivery-verified.json",
    "next": "This bounded round is complete; no active experiments, uploads or monitors. Preserve finalcohort and primary. Only next research priority is separately registered unifiedteacher-to-student distillation with verified available observations and new validation states."
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T19:32:47.369222+00:00",
    "command_verified": "python3 -m scripts.monitor_wuji_recovery_resources",
    "status": "stopped"
  },
  "recorded_finished_jobs": [
    "g0-regression-job",
    "rl-pilot20-job",
    "rl-pilot20-retry1-job",
    "reference-precheck-job",
    "rl-pilot20-retry2-job",
    "g0-regression-retry1-job",
    "pilot-evaluation-job",
    "bc-pair800-job",
    "rl-seg1-job",
    "bc800-evaluation-job",
    "bc-pair1600-job",
    "bc1600-evaluation-job",
    "bc-pair3200-job",
    "bc3200-rl250-evaluation-job",
    "bc-pair6400-job",
    "bc6400-rl500-evaluation-job",
    "bc-pair12800-job",
    "bc12800-evaluation-job",
    "rl-seg1-retry1-job",
    "bc-pair19200-job",
    "bc19200-rl1000-evaluation-job",
    "holding-precheck-job",
    "holding-precheck-retry1-job",
    "holding-precheck-retry2-job",
    "reference-pool-static-job",
    "holding-pool-static-job",
    "holding-repaired-pool-static-job",
    "rl-seg2-job",
    "reference2000-holdingmid-development-job",
    "rl-clockhold-clean-job",
    "holding2000-development-job",
    "bc-pair32000-job",
    "bc32000-development-job",
    "rl-seg3-job",
    "reference3000-development-job",
    "rl-reference-clean-job",
    "reference-clean2000-development-job",
    "bc-executed44800-job",
    "bc44800-development-job",
    "bc44800-confirmation64-job",
    "aggregation1-collection-job",
    "aggregation1-pair6400-job",
    "rl-seg4-job",
    "aggregation1-development-job",
    "reference4000-development-job",
    "aggregation1-promotion64-job",
    "bc-seed2-executed44800-job",
    "aggregation2-collection-job",
    "bc-seed2-aggregate3200-job",
    "seed2-promotion64-job",
    "final-g1-job",
    "final-g0-job",
    "local-final-S2-job",
    "local-final-S5-job",
    "local-final-S5-failure-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T20:02:27.973812+00:00",
  "next_actions": [
    "This round is finished. Preserve its immutable final cohort, weights, archives and original workspaces. Do not resume training or select checkpoints against this final set.",
    "Next round: distill this single frozen privileged teacher into a student using verified available observations/history, freeze actor, and evaluate on newly preregistered states. No more training or final-set tuning in this round."
  ],
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000",
  "training_active_runs": [],
  "bc_next_plan": "research/artmanip-recovery-20260930/bc44800-plan.json",
  "github_last_verified_commit": "4944b9c4462ce9517e3bb370f2a9c435b4e88f4c",
  "release_verified_assets": 86,
  "gpu_hours_by_host": {
    "authorized_remote": 22.35554528388888,
    "local": 0.06213329277777778
  },
  "bc_executed_endpoint": {
    "path": "runs/artmanip-recovery-20260930/bc-executed44800/E/epoch_005700.pth",
    "sha256": "2f85fa6b77b9c5358d519dcd816b285efcf33900498400dd54a8ae22bba1fac3",
    "epoch": 5700,
    "updates": 45600,
    "updates_after_BC100": 44800
  },
  "current_candidate": {
    "name": "Eagg6100",
    "path": "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
    "sha256": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "S32_passed": true,
    "S64_verified": true,
    "final_evaluated": true,
    "verification": "final-decision.json / final-integrity.json / public-verification.json",
    "final_S_passed": true,
    "final_F_passed": true
  },
  "final_freeze_sha256": "881e2989c91105e4f6fd8b6b0bfa13360cab3e9cccdad5d11e0f190375d73385",
  "final_cohort_opened": true,
  "artifact_watcher": {
    "pid": 2594428,
    "started_utc": "2026-09-30T18:31:39.183807+00:00",
    "max_seconds": 6000,
    "kind": "CPU-only artifact orchestration",
    "status": "completed",
    "heartbeat_utc": "2026-09-30T19:34:13.235193+00:00",
    "restored_models": [
      "Eagg6100",
      "Ereplay6500",
      "E500",
      "M300",
      "rl3000",
      "rlhold1500",
      "rlclean2000",
      "M4100",
      "E4100",
      "E5700",
      "rl4000",
      "rlhold2000",
      "Eagg6500",
      "bc100",
      "rl1000",
      "seed2Eagg6100",
      "historical",
      "source3"
    ],
    "gpu_hours": 22.35554528388888,
    "finished_utc": "2026-09-30T19:34:13.235452+00:00"
  },
  "final_cohort_closed": true,
  "public_release_verified": true,
  "github_scientific_commit": "cf6f6a0f861203af1335d61f17265e1bf5707d1f",
  "final_delivery": "research/artmanip-recovery-20260930/final-delivery.json",
  "final_branch_verification": "research/artmanip-recovery-20260930/branch-delivery-verified.json",
  "bounded_goal_work_complete": true
}
```
