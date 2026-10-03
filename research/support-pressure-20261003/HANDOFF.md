# Wuji 承托与持续按压当前轮

实际副本 `/data/research/artgym-experiments-20260921/support-pressure-20261003`。先读 research/support-pressure-20261003/GOAL.md 和 STATE.json。禁止子代理、自动真机动作；本轮无GPU小时上限或利用率指标。旧冻结结果不改。

```json
{
  "round_start_utc": "2026-10-03T07:27:51+00:00",
  "minimum_work_hours": 12,
  "minimum_finish_utc": "2026-10-03T19:27:51+00:00",
  "gpu_hour_cap": null,
  "gpu_utilization_requirement": null,
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
    "utc": "2026-10-03T07:53:25.416522+00:00",
    "event": "local_pressure_video_job_started",
    "evidence": "research/support-pressure-20261003/run_local_pressure_film_v7.py",
    "config": {
      "pid": 249530,
      "machine": "local4090",
      "load": 0.2,
      "detent": 0.2,
      "method": "legacyP50 fourfinger measured baseline",
      "new_measurement": "normalforces/underside moments/total addedload work"
    },
    "next": "Visualize genuinecontinuous tablepickup/40mm operation and distinguish static vs moving pressure; trainingpilot remains active",
    "state_updates": {
      "active_local_video_launcher_pid": 249530
    }
  },
  "next": "Visualize genuinecontinuous tablepickup/40mm operation and distinguish static vs moving pressure; trainingpilot remains active",
  "active_remote_launcher_pid": 217670,
  "active_local_training_pid": 246027,
  "remote_connection_status": "SSH connection timedout; v6 state unknown",
  "active_local_video_launcher_pid": 249530
}
```
