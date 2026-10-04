# Wuji 抗转动功能抓姿当前轮

实际副本 `/data/research/artgym-experiments-20260921/antirotation-grasp-20261004`。先读 research/antirotation-grasp-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-03T20:03:23+00:00",
  "minimum_work_hours": 12,
  "earliest_12h_utc": "2026-10-04T08:03:23+00:00",
  "phase": "First actual table pickup plus two-cycle functional demo passed using frozen750 and new actual contact topology; challenge load/geometry, complete delivery",
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
  "functional_demo_ready": true,
  "necessary_generalization_resolved": false,
  "hardware_ready": false,
  "real_robot_ran": false,
  "goal_complete": false,
  "active_jobs": [
    {
      "name": "actual-projected-realnominal-retain750-v4",
      "machine": "local",
      "pid": 1151666,
      "gpu": 0,
      "start_utc": "2026-10-04T01:50:32.543555+00:00"
    },
    {
      "name": "thin-table-motor-projection-complete-v4",
      "machine": "local",
      "pid": 1161150,
      "gpu": 0,
      "start_utc": "2026-10-04T02:03:57.910524+00:00"
    }
  ],
  "no_subagents": true,
  "remote_root": "/home/wangjiarui/artgym-antirotation-grasp-20261004",
  "private_attachment_media": "/tmp/wuji-antirotation-attachment-20261004",
  "next": "Dense full actual open/close approach audit before physical thin-geometry run",
  "last_event": {
    "utc": "2026-10-04T02:04:47.433549+00:00",
    "event": "thin_touch_close_projection_rejected_by_complete_acquisition",
    "config": {
      "touch_close_and_transfer_dense_passed": true,
      "complete_acquisition_passed": false,
      "minimum_actual_command_table_gap_m": -0.00012439858896201583,
      "change": "Extend same bounded original pinky/table optimization to original open target and open-to-touch segment; acceptance unchanged"
    },
    "evidence": "runs/antirotation-grasp-20261004/initial-geometry-v3/thin-projected04-reserve/acquisition-audit.json",
    "next": "Dense full actual open/close approach audit before physical thin-geometry run"
  },
  "resource_monitor_pid": 502,
  "resource_monitor_start_utc": "2026-10-03T20:15:18.833167+00:00",
  "held_bidirectional_development_ready": true,
  "github_branch": "feat/wuji-antirotation-grasp-20261004",
  "github_commit": "f1ca1446dadece78d6e5fd14974ab357222bfd13",
  "local_scientific_commit": "c78dfa5e13f20d68a31e86d03ecbbbc3f705cf83",
  "actual_table_integration_pipeline_pid": null,
  "lower_side_direct_pipeline_pid": null,
  "local_coordinate_comparison_pipeline_pid": null,
  "projected_noisy_nominal_pipeline_pid": null,
  "contact_normal_pipeline_pid": null,
  "functional_demo_scope": "Nominal/noisy initial estimate development case .2/.2 only; actual32/26mm extensions for40mmcommand, necessarygen unresolved"
}
```
