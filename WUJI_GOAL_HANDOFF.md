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
  "phase": "One legal estimated normalmoment-coordination physical pilot",
  "private_media_root": "/tmp/wuji-support-pressure-attachment-20261003",
  "remote_gpu_count_verified": 4,
  "remote_gpu_inventory_utc": "2026-10-03T07:29:00+00:00",
  "no_subagents": true,
  "no_real_robot_commands": true,
  "last_event": {
    "utc": "2026-10-03T16:06:13.822785+00:00",
    "event": "preparation_bridge_v117_verified_and_reproduce_v121_written",
    "evidence": [
      "runs/support-pressure-20261003/preparation-bridge-contract-v117/report.json",
      "research/support-pressure-20261003/REPRODUCE.md"
    ],
    "conclusion": "Fouractualprefixes contractpass, commanderror1.5635e-6rad, supportlatchedtargets29frames unchangedwithin2e-7rad, actualhistory510; incompleteoperationnotfullsuccess. Restoreguide distinguishes baseline dependencies/fullstates/learnedpilot/physicalcases/legaloffline/hardwareunknowns.",
    "next": "Publish recoverable source/result snapshot while pairedtraining remainsrunning"
  },
  "next": "Publish recoverable source/result snapshot while pairedtraining remainsrunning",
  "active_remote_launcher_pid": null,
  "active_local_training_pid": null,
  "remote_connection_status": "Persistent home SSH verified 2026-10-03 08:33 UTC; four H200 available",
  "active_local_video_launcher_pid": null,
  "github_branch": "feat/wuji-support-pressure-20261003",
  "github_commit": "b2a217d83a40a71cbba179c0006e9a9b49472a5a",
  "local_scientific_commit": "916613c7e41e32f87bdb036b04bbb3595deffb5a",
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
    7118,
    7119,
    7120
  ],
  "remote_jobs_status_utc": "2026-10-03T12:17:00Z",
  "active_remote_jobs": null,
  "remote_process_verification_utc": "2026-10-03T15:47:30Z",
  "active_remote_native_launcher_pids": []
}
```
