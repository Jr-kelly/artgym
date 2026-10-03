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
    "utc": "2026-10-03T06:44:59.214420+00:00",
    "event": "final_payload_new_assets_uploaded_and_actual_download_verified",
    "evidence": "research/robust-knife-family-20261003/downloaded-payload-batch-064459.json",
    "config": {
      "results": [
        {
          "name": "CONTACT-BEHAVIOR.md",
          "sha256": "1cc76de24c4b9bd169ae76d4df09153a177a33a7e35b0489229e0bd0d78db10e",
          "bytes": 2749
        },
        {
          "name": "contact-behavior.png",
          "sha256": "35b7d91383630302353bf2be123c82c6605fbebb2c7b67c48a002edf494a839f",
          "bytes": 495240
        },
        {
          "name": "contact-behavior.pdf",
          "sha256": "c5d39281a4007783b7255bf1c092aa1496c81c935f1f5472cee1ed342f998b47",
          "bytes": 85898
        },
        {
          "name": "contact-behavior-data.json",
          "sha256": "dfd8fe91972195e626b275b1cc5211dd1402d55ac0fa0b989cb5244ac9723afa",
          "bytes": 2116
        }
      ]
    },
    "next": "Execute actual restored code or final publication checks"
  },
  "phase": "Useful physics/training closed; final downloaded merged recovery and Release publication",
  "next": "Execute actual restored code or final publication checks",
  "active_jobs": [],
  "new_gpu_hours": 28.397893061783932,
  "cumulative_gpu_hours": 84.51588114111176,
  "remaining_gpu_hours": null,
  "active_gpu_elapsed_hours": 0,
  "remaining_including_active": null,
  "platform": "G2+Wuji v1",
  "utilization_4h_floor_percent": 27,
  "utilization_target_percent": 40,
  "latest_round_resume_utc": "2026-10-02T18:53:50+00:00",
  "pickup_first_success": "g2-sidepinch-equilibrium-v7",
  "github_branch": "feat/wuji-robust-knife-family-20261003",
  "github_commit": "77f108e02e865df45249d78d447b757fb13d3dd5",
  "local_scientific_commit": "01a3f4d7d53be1fb8f89c98b30362b011e77043d",
  "full_demo_success": true,
  "actual_history_training_audit_passed": true,
  "dense_geometry_train_count": 512,
  "full_demo_method": "Scripted G2 pickup and static preload + calibrated rolling-thumb reference + actually trained bounded P50 residual; nominal full success, independent generalization pending",
  "full_demo_evidence": "research/robust-knife-family-20261003/continuous-rolling-v30-success-v1.json",
  "learned_hybrid_full_demo_evidence": "research/robust-knife-family-20261003/learned-hybrid-full-demo-v37.json",
  "actual_g2_training_scene_audit_passed": true,
  "four_hour_gpu_utilization_verified": true,
  "four_hour_gpu_evidence": "research/robust-knife-family-20261003/resources-first-full4h.json",
  "candidate_frozen": true,
  "training_closed": true,
  "confirmation_closed": true,
  "primary_validation_complete": true,
  "gpu_work_closed": true
}
```
