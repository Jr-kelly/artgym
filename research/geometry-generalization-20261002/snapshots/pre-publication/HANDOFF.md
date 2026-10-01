# 当前 Wuji 尺寸泛化 Goal

工作区 `/data/research/artgym-experiments-20260921/geometry-generalization-20261002`。先读 research/geometry-generalization-20261002/{GOAL.md,STATE.json,HANDOFF.md,PENDING_TASKS.md,DECISIONS.jsonl}。禁止子代理；旧最终集保持关闭。PID/利用率为带时间历史记录，须重新验证。旧墙钟截止及续训方案已由新Goal替换。

```json
{
  "start_utc": "2026-10-01T21:11:50.381254+00:00",
  "base_sha": "e6c9f3e0d6167b0df529a5e7d75c88b91ff42613",
  "max_gpu_hours": 64,
  "historical_gpu_hours": 32.4534053852823,
  "new_gpu_hours": 7.93792703019248,
  "cumulative_gpu_hours": 40.39133241547478,
  "remaining_gpu_hours": 23.60866758452522,
  "reserved_final_gpu_hours": 6,
  "max_concurrent_gpus": 4,
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-geometry-20261002",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "phase": "Independent final statistical analysis and public delivery",
  "models": {
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
  },
  "goal_sha256": "9dafc220bfe1b1d3bbf1d6f7cfa21259bc8cff9410ff740156c24425365bdfb1",
  "active_jobs": [],
  "final_opened": true,
  "next": "Freeze a stable metadata copy, upload it, then commit/publish scientific deliverables",
  "last_event": {
    "utc": "2026-10-01T23:54:14.108356+00:00",
    "event": "pre_publication_metadata_snapshot_started",
    "next": "Freeze a stable metadata copy, upload it, then commit/publish scientific deliverables"
  },
  "active_gpu_elapsed_hours": 0,
  "cumulative_gpu_hours_including_active": 40.39133241547478,
  "remaining_including_active": 23.60866758452522,
  "delivery": {
    "release_id": 401374769,
    "tag": "wuji-geometry-generalization-20261002-v1",
    "draft": true,
    "published": false,
    "parent_archive": "delivery/geometry-generalization-20261002/geometry-frozen-parent-models.tar.gz",
    "parent_restore_verified": true
  },
  "confirmation_plan": "research/geometry-generalization-20261002/CONFIRMATION_PLAN.json",
  "screen_complete": true,
  "screen_protocol_runs": 78,
  "branch_selected": true,
  "camera_complete": true,
  "confirmation_conditions": [
    "baseline",
    "L80",
    "L110",
    "L120",
    "W80",
    "W110",
    "W120",
    "T80",
    "T120"
  ],
  "confirmation_complete": true,
  "principal_branch": "E→C",
  "training_started": false,
  "optimizer_updates": 0,
  "diagnostic_complete": true,
  "candidate_frozen": true,
  "candidate": "SA-real-51200",
  "final_plan": "research/geometry-generalization-20261002/FINAL_PLAN.json",
  "final_freeze_sha256": "d986f2f17450192a7b44e8bf044496a88db62597ad0d1b65acc48a981dc28f32",
  "final_protocols_completed_conditions": 12,
  "final_eval_complete": true,
  "final_protocol_runs": 78,
  "final_cohort_closed": true,
  "final_analysis_complete": true,
  "final_packets_delivered": 13,
  "report_complete": true
}
```
