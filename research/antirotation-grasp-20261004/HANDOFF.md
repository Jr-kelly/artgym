# Wuji 抗转动功能抓姿当前轮

实际副本 `/data/research/artgym-experiments-20260921/antirotation-grasp-20261004`。先读 research/antirotation-grasp-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-03T20:03:23+00:00",
  "minimum_work_hours": 12,
  "earliest_12h_utc": "2026-10-04T08:03:23+00:00",
  "phase": "Low-load held bidirectional behavior achieved; continuous pickup/preform and high-load retraction unresolved",
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
      "name": "geometry-retained-pickup-opposed-index-v1-retry1",
      "machine": "local",
      "pid": 985285,
      "gpu": 0,
      "start_utc": "2026-10-03T21:50:06.731461+00:00"
    }
  ],
  "no_subagents": true,
  "remote_root": "/home/wangjiarui/artgym-antirotation-grasp-20261004",
  "private_attachment_media": "/tmp/wuji-antirotation-attachment-20261004",
  "next": "Commit explicitnewround source/docs, continue mechanicalgrasp entrywork",
  "last_event": {
    "utc": "2026-10-03T21:51:35.798920+00:00",
    "event": "recoverable_source_snapshot_prepared",
    "evidence": "research/antirotation-grasp-20261004/PROGRESS.md",
    "conclusion": "Code and honest development outcomes prepared for interim localcommit; no newRelease/fullcontinuous/gen claim.",
    "next": "Commit explicitnewround source/docs, continue mechanicalgrasp entrywork"
  },
  "resource_monitor_pid": 502,
  "resource_monitor_start_utc": "2026-10-03T20:15:18.833167+00:00",
  "held_bidirectional_development_ready": true
}
```
