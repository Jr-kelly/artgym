# 当前统一 student Goal

工作区 `/data/research/artgym-experiments-20260921/unified-student-20261001`

先读 research/unified-student-20261001/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。禁止子代理；旧teacher最终集关闭。PID/利用率须重新核验，不据旧日志重启。

```json
{
  "start_utc": "2026-10-01T06:03:30+00:00",
  "deadline_utc": "2026-10-01T22:03:30+00:00",
  "ordinary_cutoff_utc": "2026-10-01T20:33:30+00:00",
  "max_gpu_hours": 64,
  "max_concurrent_gpus": 4,
  "reserved_final_gpu_hours": 6,
  "reserved_final_seconds": 5400,
  "gpu_hours": 0.166339191198349,
  "phase": "Teacher restoration and whole-policy input audit",
  "active_jobs": [],
  "base_sha": "56d4dcc66e805298cb5f4c365a55f9c14df36b37",
  "teacher_sha256": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-student-20261001",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "goal_sha256": "c7e9c244d11824a5d230cfb24ac9207e78fcb1965a376bff6a38f03c084c4a3f",
  "existing_student_run_found": false,
  "prior_session": "Previous user turn performed only read-only attachment/connectivity check; no studentgoal/training/worktree existed. Prior teacher round closed.",
  "next": "Restore runtime and exactteacher, inspect full observation/action/RNN interface and register new states before training.",
  "last_event": {
    "utc": "2026-10-01T06:22:14.520426+00:00",
    "event": "condition_checks_registered",
    "evidence": "research/unified-student-20261001/data/conditions.json",
    "scope": "S5 oldfixed failures rows96and97 with source0/1/2 controls; preserve first5slots acrossbatch/render comparisons",
    "next": "Launch after devices release; primary config officialactuator andseed2026093031"
  }
}
```
