# Wuji 承托与持续按压当前轮

实际副本 `/data/research/artgym-experiments-20260921/support-pressure-20261003`。先读 research/support-pressure-20261003/GOAL.md 和 STATE.json。禁止子代理、自动真机动作；本轮无GPU小时上限；利用率按STATE中的最新用户规则。旧冻结结果不改。

```json
{
  "round_start_utc": "2026-10-03T07:27:51+00:00",
  "minimum_work_hours": 12,
  "minimum_finish_utc": "2026-10-03T19:27:51+00:00",
  "gpu_hour_cap": null,
  "gpu_utilization_requirement": {
    "whole_machine_4h_floor_percent": 26,
    "running_target_above_percent": 40,
    "source": "Latest direct user-provided AGENTS.md"
  },
  "platform": "G2+Wuji v1",
  "baseline_local_commit": "995f5acd72f4038b1b3ca3be921248620975d54a",
  "baseline_github_commit": "6afe8270735abf91b86b001803150e542d720111",
  "baseline_release": "wuji-g2-continuous-knife-robust-20261003-v1",
  "goal_complete": false,
  "phase": "First contact-force calibration and actual control modification",
  "private_media_root": "/tmp/wuji-support-pressure-attachment-20261003",
  "remote_gpu_count_verified": 4,
  "remote_gpu_inventory_utc": "2026-10-03T07:29:00+00:00",
  "no_subagents": true,
  "no_real_robot_commands": true,
  "last_event": {
    "utc": "2026-10-03T09:27:08.657311+00:00",
    "event": "portable_initial_estimate_continuous_entrypoint_added",
    "evidence": "scripts/run_wuji_support_demo.py",
    "conclusion": "Uses same commonplanner and actualcontinuous runner, explicitseparation of noisyinitial observation fromphysicalasset. CLIhelp verified; fullrestoredexecution pendingfinalcandidate, no hardwareSDK invented.",
    "next": "Closeactiveexperimentpairs, execute two boundedknownstroke trials and preserve newsource/configsnapshot"
  },
  "next": "Closeactiveexperimentpairs, execute two boundedknownstroke trials and preserve newsource/configsnapshot",
  "active_remote_launcher_pid": null,
  "active_local_training_pid": null,
  "remote_connection_status": "Persistent home SSH verified 2026-10-03 08:33 UTC; four H200 available",
  "active_local_video_launcher_pid": null,
  "github_branch": "feat/wuji-support-pressure-20261003",
  "github_commit": "dd8762112a603e39b6f736dc2915ffcdb74b8ee6",
  "local_scientific_commit": "e3c7ed19231d6255a0fb7ff30b2ec36d3656e56f",
  "remote_root": "/home/wangjiarui/artgym-support-pressure-20261003",
  "active_remote_training_jobs": [
    "joint-base-continuation-v31",
    "joint-noisier-continuation-v31",
    "joint-looser-v34",
    "joint-pressure-v34"
  ],
  "active_remote_demo_launcher_pid": null,
  "active_remote_variant_launcher_pid": null,
  "active_remote_learned_check_launcher_pid": null,
  "active_remote_inward_launcher_pid": null,
  "active_remote_training_launcher_pid": null,
  "active_remote_cooperative_launcher_pid": null,
  "active_remote_estimate_launcher_pid": null,
  "active_remote_joint_estimate_launcher_pid": null,
  "active_remote_pressure_tier_launcher_pid": null,
  "active_remote_resource_sampler_pid": 6329,
  "active_remote_training_launcher_pids": [
    7704,
    7705,
    8220,
    8221
  ]
}
```
