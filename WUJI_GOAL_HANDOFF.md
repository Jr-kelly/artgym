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
  "phase": "Last matched support-coordinate pilot; portable delivery preparation",
  "private_media_root": "/tmp/wuji-support-pressure-attachment-20261003",
  "remote_gpu_count_verified": 4,
  "remote_gpu_inventory_utc": "2026-10-03T07:29:00+00:00",
  "no_subagents": true,
  "no_real_robot_commands": true,
  "last_event": {
    "utc": "2026-10-03T16:56:49.069818+00:00",
    "event": "normal_coordinate_early_offline_v129_closed_four_pilots_running",
    "phase": "Last matched support-coordinate pilot; portable delivery preparation",
    "evidence": "runs/support-pressure-20261003/offline-normal-coordinate-replay-v129/report.json",
    "config": {
      "replay_commands": 651,
      "max_target_difference_rad": 1.3113021850585938e-06,
      "instant_verification_utc": "2026-10-03T16:53:40Z",
      "gpu_instant_percent": [
        74,
        77,
        75,
        84
      ],
      "whole_machine_instant_percent": 77.5
    },
    "conclusion": "Serializedreferenceactor/basis works onlegal-only14.3s takeover,651commands, max1.31e-6rad difference. No physics orhardwareperformanceclaim. AllfourGPUjobs perform usefulmatched joint/normal × jointthumb/frozenthumb continuouslearning; laterrolling4h requirementnotyetverified asmet.",
    "next": "Finish100update pilots,8 nativecases maximum, freeze and4 independentcases, recovery/video/newRelease",
    "state_updates": {
      "active_remote_training_launcher_pids": [
        10753,
        10754,
        10755,
        11749
      ],
      "active_remote_native_launcher_pids": [],
      "remote_process_verification_utc": "2026-10-03T16:53:40Z"
    }
  },
  "next": "Finish100update pilots,8 nativecases maximum, freeze and4 independentcases, recovery/video/newRelease",
  "active_remote_launcher_pid": null,
  "active_local_training_pid": null,
  "remote_connection_status": "Persistent home SSH verified 2026-10-03 08:33 UTC; four H200 available",
  "active_local_video_launcher_pid": null,
  "github_branch": "feat/wuji-support-pressure-20261003",
  "github_commit": "0751e03b957e88c74d4774fa8c93467ed9daea49",
  "local_scientific_commit": "6cd00db8b8f6ad9a50e0649e47b6574221186134",
  "remote_root": "/home/wangjiarui/artgym-support-pressure-20261003",
  "active_remote_training_jobs": [],
  "active_remote_demo_launcher_pid": null,
  "active_remote_variant_launcher_pid": null,
  "active_remote_learned_check_launcher_pid": null,
  "active_remote_inward_launcher_pid": null,
  "active_remote_training_launcher_pid": null,
  "active_remote_cooperative_launcher_pid": null,
  "active_remote_estimate_launcher_pid": null,
  "active_remote_joint_estimate_launcher_pid": null,
  "active_remote_pressure_tier_launcher_pid": null,
  "active_remote_resource_sampler_pid": 476,
  "active_remote_training_launcher_pids": [
    10753,
    10754,
    10755,
    11749
  ],
  "remote_jobs_status_utc": "2026-10-03T12:17:00Z",
  "active_remote_jobs": null,
  "remote_process_verification_utc": "2026-10-03T16:53:40Z",
  "active_remote_native_launcher_pids": []
}
```
