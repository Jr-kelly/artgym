# 当前 Wuji 桌面拿取到伸缩完整仿真 Goal

工作区 `/data/research/artgym-experiments-20260921/robust-knife-family-20261003`。先读 research/robust-knife-family-20261003/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。禁止子代理；旧最终集关闭。PID/利用率均须重新核实。

```json
{
  "start_utc": "2026-10-02T18:10:15.396393+00:00",
  "historical_gpu_hours": 56.11798807932783,
  "gpu_hour_cap": null,
  "budget_policy": "No GPU-hour cap; previous64 and reserve limits explicitly superseded",
  "minimum_useful_work_hours": 12,
  "max_concurrent_gpus": 4,
  "models": {
    "runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth": "bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd",
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8"
  },
  "remote_inventory_verified": true,
  "remote_additional_consumption_unknown": false,
  "goal_complete": false,
  "last_event": {
    "utc": "2026-10-03T05:30:02.257102+00:00",
    "event": "closed_validation_and_secondary_reports_git_staging",
    "config": {
      "eligible_files": 522,
      "excluded_private_and_user_artifacts": [
        "research/robust-knife-family-20261003/build_franka.py",
        "research/robust-knife-family-20261003/.event.lock",
        "research/robust-knife-family-20261003/middle-feedback-figure-v1/manifest.json",
        "research/robust-knife-family-20261003/middle-feedback-figure-v1/middle-feedback.pdf",
        "research/robust-knife-family-20261003/middle-feedback-figure-v1/middle-feedback.png",
        "research/robust-knife-family-20261003/paired-capacity-figure-v1/paired-capacity.pdf",
        "research/robust-knife-family-20261003/paired-capacity-figure-v1/manifest.json",
        "research/robust-knife-family-20261003/paired-capacity-figure-v1/paired-capacity.png",
        "research/robust-knife-family-20261003/media/GOAL.txt",
        "research/robust-knife-family-20261003/media/media-1.jpg",
        "research/robust-knife-family-20261003/media/manifest.json",
        "research/robust-knife-family-20261003/media/media-3.mp4",
        "research/robust-knife-family-20261003/media/media-0.jpg",
        "research/robust-knife-family-20261003/media/MEDIA.json"
      ]
    },
    "conclusion": "ExplicitD-only staging; noFranka/privatehumanmedia orfrozenruntime modifications",
    "next": "Commit exactclosed evidence thenpublish mappedGit tree insequence"
  },
  "phase": "Frozen P50 primary validation and recoverable GitHub delivery",
  "next": "Commit exactclosed evidence thenpublish mappedGit tree insequence",
  "active_jobs": [],
  "new_gpu_hours": 26.96529086304533,
  "cumulative_gpu_hours": 83.08327894237316,
  "remaining_gpu_hours": null,
  "active_gpu_elapsed_hours": 0,
  "remaining_including_active": null,
  "platform": "G2+Wuji v1",
  "utilization_4h_floor_percent": 27,
  "utilization_target_percent": 40,
  "latest_round_resume_utc": "2026-10-02T18:53:50+00:00",
  "pickup_first_success": "g2-sidepinch-equilibrium-v7",
  "github_branch": "feat/wuji-robust-knife-family-20261003",
  "github_commit": "186afae40d6a512290b4f4fe0ce5011941a6c1e8",
  "local_scientific_commit": "3d058d2ffb0c057dbc5165862aa6524909c4fbd4",
  "full_demo_success": true,
  "actual_history_training_audit_passed": true,
  "dense_geometry_train_count": 512,
  "full_demo_method": "Scripted G2 pickup and static preload + calibrated rolling-thumb reference + actually trained bounded P50 residual; nominal full success, independent generalization pending",
  "full_demo_evidence": "research/robust-knife-family-20261003/continuous-rolling-v30-success-v1.json",
  "learned_hybrid_full_demo_evidence": "research/robust-knife-family-20261003/learned-hybrid-full-demo-v37.json",
  "actual_g2_training_scene_audit_passed": true,
  "four_hour_gpu_utilization_verified": true,
  "four_hour_gpu_evidence": "research/robust-knife-family-20261003/resources-first-full4h.json",
  "candidate_frozen": true
}
```
