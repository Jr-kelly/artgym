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
  "gpu_hours": 32.4534053852823,
  "phase": "Finalnegativecapabilityresultverified; CPUpublicdeliveryremaining",
  "active_jobs": [],
  "base_sha": "56d4dcc66e805298cb5f4c365a55f9c14df36b37",
  "teacher_sha256": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-student-20261001",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "goal_sha256": "c7e9c244d11824a5d230cfb24ac9207e78fcb1965a376bff6a38f03c084c4a3f",
  "existing_student_run_found": false,
  "prior_session": "Previous user turn performed only read-only attachment/connectivity check; no studentgoal/training/worktree existed. Prior teacher round closed.",
  "next": "Commitpushscientificdelivery thenpublishReleaseatthatcommit; actuallydownloadprimaryand4videos",
  "last_event": {
    "utc": "2026-10-01T20:03:54.941389+00:00",
    "event": "all28_release_asset_bytes_and_server_digests_verified",
    "evidence": "/data/research/artgym-experiments-20260921/unified-student-20261001/research/unified-student-20261001/public-manifest.json",
    "asset_count": 28,
    "total_bytes": 9478824470,
    "next": "Commitpushscientificdelivery thenpublishReleaseatthatcommit; actuallydownloadprimaryand4videos"
  },
  "research_notes": "research/unified-student-20261001/RESEARCH_NOTES.md",
  "current_plan": "research/unified-student-20261001/fixed-method-extension70400-plan.json",
  "repair_count": 2,
  "current_evaluation_plans": [
    "research/unified-student-20261001/extension70400-SC-evaluation-queue.json",
    "research/unified-student-20261001/extension70400-SA-evaluation-queue.json"
  ],
  "supplemental_plan": "research/unified-student-20261001/controller-long-budget-plan.json",
  "evaluation_gpu_assignments": {
    "extension70400-SC-evaluation-queue.json": 3,
    "extension70400-SA-evaluation-queue.json": 1
  },
  "provisional_best_development": {
    "name": "SA-real-51200",
    "checkpoint": "runs/unified-student-20261001/SA-real-51200/step_051200.pth",
    "sha256": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9",
    "worst_strict_count": 24,
    "worst_stage_hold": 0.75,
    "n": 32,
    "full_gate": false,
    "final_selected": false
  },
  "delivery_progress": {
    "last_pushed_commit": "bd866a317f9560a158a06ce9ed95b1f860b7a195",
    "release_id": 400860039,
    "tag": "wuji-unified-student-20261001-v1",
    "draft": true,
    "uploaded_assets": 28,
    "upload_receipts": [
      "research/unified-student-20261001/upload-development-first3.json",
      "research/unified-student-20261001/upload-source-history.json",
      "research/unified-student-20261001/upload-through25600.json",
      "research/unified-student-20261001/upload-through38400.json",
      "research/unified-student-20261001/upload-paired-teacher-video.json",
      "research/unified-student-20261001/upload-runtime-provenance44800.json",
      "research/unified-student-20261001/upload-training51200.json",
      "research/unified-student-20261001/upload-development51200.json",
      "research/unified-student-20261001/upload-source51200.json",
      "research/unified-student-20261001/upload-training64000.json",
      "research/unified-student-20261001/upload-development64000.json",
      "research/unified-student-20261001/upload-source64000.json",
      "research/unified-student-20261001/upload-training70400.json",
      "research/unified-student-20261001/upload-development70400.json",
      "research/unified-student-20261001/upload-original-failure-video.json",
      "research/unified-student-20261001/upload-student-videos.json",
      "research/unified-student-20261001/upload-video-evidence.json",
      "research/unified-student-20261001/upload-final-source.json",
      "research/unified-student-20261001/upload-final-traces-streamed.json",
      "research/unified-student-20261001/upload-primary.json",
      "research/unified-student-20261001/upload-final-metadata.json"
    ],
    "teacher_paired_video": "delivery/unified-student-20261001/teacher-paired-four-sources.mp4",
    "student_video_pending": false,
    "final_cohort_opened": true
  },
  "verification_helpers": [
    "scripts/audit_wuji_student_final.py",
    "scripts/verify_wuji_student_public.py"
  ],
  "ordinary_training_endpoint": 70400,
  "final_freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
  "training_active_runs": [],
  "final_cohort_closed": true,
  "final_result": {
    "primary": "SA-real-51200",
    "full_gate_pass": false,
    "worst_source": 3,
    "worst_protocol": "S2",
    "strict": 93,
    "n": 128,
    "body": 121
  },
  "monitor": {
    "pid": 4059290,
    "status": "stopped",
    "evidence": "research/unified-student-20261001/resources-final.json"
  }
}
```
