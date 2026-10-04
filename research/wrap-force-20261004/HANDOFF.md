# Wuji 包覆承托与轴向测力当前轮

实际副本 `/data/research/artgym-experiments-20260921/wrap-force-20261004`。先读 research/wrap-force-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-04T10:51:40.525679+00:00",
  "minimum_work_hours": 12,
  "minimum_finish_utc": "2026-10-04T22:51:40.525679+00:00",
  "phase": "Continuous source2 functional grip adaptation and corrected geometry observation",
  "baseline_release": "wuji-g2-antirotation-grasp-20261004-v1",
  "baseline_local_commit": "29825ad91b7075b080f96e65370f49a0201c614b",
  "baseline_github_commit": "b892d8909efb9da33407b02e6ffd229f7d6f00b4",
  "baseline_tag_commit": "59eb7833c565b857a28f5016a7b11dc8e2eb013e",
  "gpu_hour_cap": null,
  "no_subagents": true,
  "no_real_robot_commands": true,
  "delivery_complete": false,
  "functional_demo_ready": true,
  "necessary_generalization_resolved": false,
  "hardware_ready": false,
  "real_robot_ran": false,
  "goal_complete": false,
  "axial_force_measurement_resolved": false,
  "active_jobs": [],
  "remote_gpu_inventory": {
    "verified_utc": "2026-10-04T10:51:40.525679+00:00",
    "count": 4,
    "name": "NVIDIA H200",
    "initially_idle": true
  },
  "next": "Publishverifiedcurrentroundscienceafter12h, thenupdatecompletedpublicreceipt",
  "last_event": {
    "utc": "2026-10-04T22:44:57.495638+00:00",
    "event": "public_resource_statement_updated",
    "evidence": "research/wrap-force-20261004/FINAL-REPORT.md",
    "conclusion": "Explicitlatestapprox4h development4.63% missesfloor; local29.12%misses40target. Oldpartialstatusnotcurrentfact; snapshotPIDscopeexplicit.",
    "next": "Publishverifiedcurrentroundscienceafter12h, thenupdatecompletedpublicreceipt"
  },
  "baseline_functional_demo_ready": true,
  "local_resource_monitor_pid": 3068820,
  "github_branch": "feat/wuji-wrap-force-20261004",
  "github_commit": "1302a4be79f2b92802ea0510fad8fd5a6bfca1c5",
  "local_scientific_commit": "4a7fe7d91a0c0736e2e36944809557072982ed0e",
  "multigrasp_comparison_required_before_long_training": true,
  "multigrasp_comparison_completed": true,
  "geometry_split_preserved": {
    "train": "000–011",
    "heldout": "012–015"
  },
  "endpoint_reference": "position above rail lower stop, not returned distance",
  "multigrasp_initial_comparison_completed": true,
  "development_resource_monitor_pid": 1896,
  "operational_grasp_selected": "newindexwrap direct mass-awarecornerpickup + S120 + .8jointpressureproxy",
  "single_vs_multi_training_eligible_after_batch_parity": true,
  "small_batch_interface_passed": true,
  "small_batch_behavior_parity_passed": true,
  "long_training_automatic_promotion": false,
  "development_connection_state": "SSHrestored, runtimeverified and targetedcomparison running",
  "development_training_launch_confirmed": false,
  "geometry_held_submodule_pass": true,
  "promising_continuous_candidate": "continuous-thumb25 update50; functional allchecks exceptfinalsettling",
  "diagnostic_axial_force_measured": true
}
```
