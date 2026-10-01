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
  "gpu_hours": 24.4922556702296,
  "phase": "SC/SA51200to64000 running; bestSA51200; finalunopened",
  "active_jobs": [
    {
      "name": "SA-real-64000",
      "gpu": 0,
      "seconds": 12000,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.train_wuji_unified_student",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--output",
        "runs/unified-student-20261001/SA-real-64000",
        "--kind",
        "SC",
        "--controller-mode",
        "real",
        "--updates",
        "64000",
        "--resume",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth",
        "--save-at",
        "54400",
        "57600",
        "60800",
        "64000",
        "--envs",
        "256",
        "--rollout-steps",
        "4",
        "--seed",
        "61001",
        "--lr",
        ".0003",
        "--warm-updates",
        "400",
        "--target-loss-weight",
        "25",
        "--target-loss-scale",
        ".04"
      ],
      "start_utc": "2026-10-01T16:03:27.387515+00:00",
      "local_pid": 3518206,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "91beb367ba0a0f9e8f73e51aec48cf8473ad98bcba64a1912cf35d7b7b26742c",
      "pinned_source_sha256": "91beb367ba0a0f9e8f73e51aec48cf8473ad98bcba64a1912cf35d7b7b26742c",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/SA-real-64000 && CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 12000 /tmp/wuji-student-runtime/bin/python -m scripts.train_wuji_unified_student --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --output runs/unified-student-20261001/SA-real-64000 --kind SC --controller-mode real --updates 64000 --resume runs/unified-student-20261001/SA-real-51200/step_051200.pth --save-at 54400 57600 60800 64000 --envs 256 --rollout-steps 4 --seed 61001 --lr .0003 --warm-updates 400 --target-loss-weight 25 --target-loss-scale .04"
    },
    {
      "name": "SC-real-64000",
      "gpu": 2,
      "seconds": 12000,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.train_wuji_unified_student",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--output",
        "runs/unified-student-20261001/SC-real-64000",
        "--kind",
        "SC",
        "--controller-mode",
        "real",
        "--updates",
        "64000",
        "--resume",
        "runs/unified-student-20261001/SC-real-51200/step_051200.pth",
        "--save-at",
        "54400",
        "57600",
        "60800",
        "64000",
        "--envs",
        "256",
        "--rollout-steps",
        "4",
        "--seed",
        "61001",
        "--lr",
        ".0003",
        "--warm-updates",
        "400",
        "--target-loss-weight",
        "0",
        "--target-loss-scale",
        ".04"
      ],
      "start_utc": "2026-10-01T16:03:26.143219+00:00",
      "local_pid": 3518026,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "91beb367ba0a0f9e8f73e51aec48cf8473ad98bcba64a1912cf35d7b7b26742c",
      "pinned_source_sha256": "91beb367ba0a0f9e8f73e51aec48cf8473ad98bcba64a1912cf35d7b7b26742c",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/SC-real-64000 && CUDA_VISIBLE_DEVICES=2 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 12000 /tmp/wuji-student-runtime/bin/python -m scripts.train_wuji_unified_student --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --output runs/unified-student-20261001/SC-real-64000 --kind SC --controller-mode real --updates 64000 --resume runs/unified-student-20261001/SC-real-51200/step_051200.pth --save-at 54400 57600 60800 64000 --envs 256 --rollout-steps 4 --seed 61001 --lr .0003 --warm-updates 400 --target-loss-weight 0 --target-loss-scale .04"
    }
  ],
  "base_sha": "56d4dcc66e805298cb5f4c365a55f9c14df36b37",
  "teacher_sha256": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-student-20261001",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "goal_sha256": "c7e9c244d11824a5d230cfb24ac9207e78fcb1965a376bff6a38f03c084c4a3f",
  "existing_student_run_found": false,
  "prior_session": "Previous user turn performed only read-only attachment/connectivity check; no studentgoal/training/worktree existed. Prior teacher round closed.",
  "next": "Continue64000stage; finalprimary/finalcohort/video/publicrestore pending; do not closegoal",
  "last_event": {
    "utc": "2026-10-01T16:08:24.583019+00:00",
    "event": "51200_completed_evidence_uploaded_and_source_restored",
    "evidence": [
      "research/unified-student-20261001/upload-development51200.json",
      "research/unified-student-20261001/upload-source51200.json",
      "research/unified-student-20261001/source51200-local-restore.json"
    ],
    "release_assets": 15,
    "draft": true,
    "restored_source_pins": 10,
    "next": "Continue64000stage; finalprimary/finalcohort/video/publicrestore pending; do not closegoal"
  },
  "research_notes": "research/unified-student-20261001/RESEARCH_NOTES.md",
  "current_plan": "research/unified-student-20261001/fixed-method-extension64000-plan.json",
  "repair_count": 2,
  "current_evaluation_plans": [
    "research/unified-student-20261001/extension64000-SC-evaluation-queue.json",
    "research/unified-student-20261001/extension64000-SA-evaluation-queue.json"
  ],
  "supplemental_plan": "research/unified-student-20261001/controller-long-budget-plan.json",
  "evaluation_gpu_assignments": {
    "extension64000-SC-evaluation-queue.json": 3,
    "extension64000-SA-evaluation-queue.json": 1
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
    "last_pushed_commit": "ad14975",
    "release_id": 400860039,
    "tag": "wuji-unified-student-20261001-v1",
    "draft": true,
    "uploaded_assets": 15,
    "upload_receipts": [
      "research/unified-student-20261001/upload-development-first3.json",
      "research/unified-student-20261001/upload-source-history.json",
      "research/unified-student-20261001/upload-through25600.json",
      "research/unified-student-20261001/upload-through38400.json",
      "research/unified-student-20261001/upload-paired-teacher-video.json",
      "research/unified-student-20261001/upload-runtime-provenance44800.json",
      "research/unified-student-20261001/upload-training51200.json",
      "research/unified-student-20261001/upload-development51200.json",
      "research/unified-student-20261001/upload-source51200.json"
    ],
    "teacher_paired_video": "delivery/unified-student-20261001/teacher-paired-four-sources.mp4",
    "student_video_pending": true,
    "final_cohort_opened": false
  },
  "verification_helpers": [
    "scripts/audit_wuji_student_final.py",
    "scripts/verify_wuji_student_public.py"
  ]
}
```
