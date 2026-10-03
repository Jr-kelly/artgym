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
  "phase": "All boundeddevelopmentlearning closed; finalrecoverableRelease delivery",
  "private_media_root": "/tmp/wuji-support-pressure-attachment-20261003",
  "remote_gpu_count_verified": 4,
  "remote_gpu_inventory_utc": "2026-10-03T07:29:00+00:00",
  "no_subagents": true,
  "no_real_robot_commands": true,
  "last_event": {
    "utc": "2026-10-03T19:27:25.647777+00:00",
    "event": "final_publication_receipt_assets_and_release_notes_verified",
    "config": {
      "assets": 32,
      "tag": "wuji-g2-support-pressure-20261003-v1",
      "immutable_tag_commit": "4a5c1d813325951fe74f792042ba23690d9c2442"
    },
    "next": "Finalpersistentsource/endinghandoff snapshot; no pendingexperiments orhardwareactions",
    "state_updates": {
      "release_assets_verified": 32,
      "public_download_verification_complete": true,
      "all_experiments_closed": true
    }
  },
  "next": "Finalpersistentsource/endinghandoff snapshot; no pendingexperiments orhardwareactions",
  "active_remote_launcher_pid": null,
  "active_local_training_pid": null,
  "remote_connection_status": "Persistent home SSH verified 2026-10-03 08:33 UTC; four H200 available",
  "active_local_video_launcher_pid": null,
  "github_branch": "feat/wuji-support-pressure-20261003",
  "github_commit": "4a5c1d813325951fe74f792042ba23690d9c2442",
  "local_scientific_commit": "abf6ad32d7a344990044be654af8782c92139768",
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
  "active_remote_resource_sampler_pid": null,
  "active_remote_training_launcher_pids": [],
  "remote_jobs_status_utc": "2026-10-03T12:17:00Z",
  "active_remote_jobs": null,
  "remote_process_verification_utc": "2026-10-03T19:21:39.769443+00:00",
  "active_remote_native_launcher_pids": [],
  "candidate_frozen": true,
  "training_closed": true,
  "necessary_generalization_resolved": false,
  "independent_validation_complete": true,
  "new_independent_physical_attempts": 4,
  "new_independent_successes": 0,
  "actual_restored_startup_complete": true,
  "actual_restored_startup_full_success": true,
  "active_remote_observer_head_launcher": null,
  "frozen_candidate_training_closed": true,
  "active_remote_observer_training_launchers": null,
  "active_remote_observer_native_launchers": null,
  "observer_route_adopted": false,
  "release_public": true,
  "release_url": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-support-pressure-20261003-v1",
  "release_assets_verified": 32,
  "public_download_verification_complete": true,
  "all_experiments_closed": true
}
```
