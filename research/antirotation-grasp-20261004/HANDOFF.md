# Wuji 抗转动功能抓姿当前轮

实际副本 `/data/research/artgym-experiments-20260921/antirotation-grasp-20261004`。先读 research/antirotation-grasp-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-03T20:03:23+00:00",
  "minimum_work_hours": 12,
  "earliest_12h_utc": "2026-10-04T08:03:23+00:00",
  "phase": "Newpreform actualtablepickup achieved; connectactualsettledgrip to2loadedcycles and necessarygeneralization",
  "baseline_local_commit": "b75e12effbfb5a9ce740411b5ec699db60338b3e",
  "baseline_github_commit": "d0d6ce01d5550ec5b512fdc4e510c5546569d8b4",
  "baseline_release": "wuji-g2-support-pressure-20261003-v1",
  "gpu_hour_cap": null,
  "gpu_utilization_rule": {
    "whole_machine_4h_floor_percent": 26,
    "running_target_above_percent": 40,
    "source": "CurrentAGENTS.md; usefulcomputationonly, no concealed/filler jobs"
  },
  "delivery_complete": false,
  "functional_demo_ready": false,
  "necessary_generalization_resolved": false,
  "hardware_ready": false,
  "real_robot_ran": false,
  "goal_complete": false,
  "active_jobs": [
    {
      "name": "opposed-picked-up-issued-anchor-posture-preload-v4",
      "machine": "local",
      "pid": 1031628,
      "gpu": 0,
      "start_utc": "2026-10-03T22:55:31.073788+00:00"
    }
  ],
  "no_subagents": true,
  "remote_root": "/home/wangjiarui/artgym-antirotation-grasp-20261004",
  "private_attachment_media": "/tmp/wuji-antirotation-attachment-20261004",
  "next": "Finish currentreference and immediateactualcontinuous behavior; then actualpickup randomization training",
  "last_event": {
    "utc": "2026-10-03T23:02:09.333919+00:00",
    "event": "legacy_bridge_regression_and_new_table_scene_prepared",
    "evidence": [
      "runs/antirotation-grasp-20261004/offline-core-controller-regression-v3/replay/report.json",
      "runs/antirotation-grasp-20261004/offline-core-controller-regression-v3/timing.json",
      "research/antirotation-grasp-20261004/actual-table-strong-scene-v1.json"
    ],
    "conclusion": "600 actualrecordframes, frozen750 targets differ at most5.960464477539062e-7rad; prewarmed maximum4.738ms, no30Hz overruns. Offline only. Newactualpickup scene and knownsupportspan prepared; no newtraining launched or success inferred.",
    "next": "Finish currentreference and immediateactualcontinuous behavior; then actualpickup randomization training"
  },
  "resource_monitor_pid": 502,
  "resource_monitor_start_utc": "2026-10-03T20:15:18.833167+00:00",
  "held_bidirectional_development_ready": true,
  "github_branch": "feat/wuji-antirotation-grasp-20261004",
  "github_commit": "39afd113e32ad85c4132a1a5c6f27a1484edf4bf",
  "local_scientific_commit": "85a3baa2103eb2084d640d35d78d4e54eadbfb97"
}
```
