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
  "gpu_hours": 31.809391034907765,
  "phase": "Frozenfinalteacherprimaryendpointcontrolrunning; C1next",
  "active_jobs": [
    {
      "name": "final-SA-real-70400",
      "gpu": 2,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_student_batch",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--models",
        "SA-real-70400=runs/unified-student-20261001/SA-real-70400/step_070400.pth",
        "--states",
        "research/unified-student-20261001/data/final-all.npy",
        "--output",
        "runs/unified-student-20261001/final-SA-real-70400"
      ],
      "start_utc": "2026-10-01T19:31:41.493958+00:00",
      "local_pid": 655335,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
      "frozen_models_used": [
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "runs/unified-student-20261001/SA-real-70400/step_070400.pth"
      ],
      "final_cohort_sha256": "a47be7464659f75e69ef6f7165a7b057a0fd433ed180af76723f9bb5e1576a82",
      "pinned_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/final-SA-real-70400 && CUDA_VISIBLE_DEVICES=2 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.evaluate_wuji_student_batch --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --models SA-real-70400=runs/unified-student-20261001/SA-real-70400/step_070400.pth --states research/unified-student-20261001/data/final-all.npy --output runs/unified-student-20261001/final-SA-real-70400"
    },
    {
      "name": "final-teacher",
      "gpu": 0,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_student_batch",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--models",
        "teacher=teacher",
        "--states",
        "research/unified-student-20261001/data/final-all.npy",
        "--output",
        "runs/unified-student-20261001/final-teacher"
      ],
      "start_utc": "2026-10-01T19:31:39.037821+00:00",
      "local_pid": 655059,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
      "frozen_models_used": [
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth"
      ],
      "final_cohort_sha256": "a47be7464659f75e69ef6f7165a7b057a0fd433ed180af76723f9bb5e1576a82",
      "pinned_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/final-teacher && CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.evaluate_wuji_student_batch --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --models teacher=teacher --states research/unified-student-20261001/data/final-all.npy --output runs/unified-student-20261001/final-teacher"
    },
    {
      "name": "final-SA-real-51200",
      "gpu": 1,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_student_batch",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--models",
        "SA-real-51200=runs/unified-student-20261001/SA-real-51200/step_051200.pth",
        "--states",
        "research/unified-student-20261001/data/final-all.npy",
        "--output",
        "runs/unified-student-20261001/final-SA-real-51200"
      ],
      "start_utc": "2026-10-01T19:31:40.221504+00:00",
      "local_pid": 655198,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
      "frozen_models_used": [
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth"
      ],
      "final_cohort_sha256": "a47be7464659f75e69ef6f7165a7b057a0fd433ed180af76723f9bb5e1576a82",
      "pinned_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/final-SA-real-51200 && CUDA_VISIBLE_DEVICES=1 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.evaluate_wuji_student_batch --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --models SA-real-51200=runs/unified-student-20261001/SA-real-51200/step_051200.pth --states research/unified-student-20261001/data/final-all.npy --output runs/unified-student-20261001/final-SA-real-51200"
    },
    {
      "name": "final-SC-real-51200",
      "gpu": 3,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_student_batch",
        "--teacher",
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "--models",
        "SC-real-51200=runs/unified-student-20261001/SC-real-51200/step_051200.pth",
        "--states",
        "research/unified-student-20261001/data/final-all.npy",
        "--output",
        "runs/unified-student-20261001/final-SC-real-51200"
      ],
      "start_utc": "2026-10-01T19:31:42.696893+00:00",
      "local_pid": 655509,
      "remote_root": "/tmp/artgym-student-20261001",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
      "frozen_models_used": [
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "runs/unified-student-20261001/SC-real-51200/step_051200.pth"
      ],
      "final_cohort_sha256": "a47be7464659f75e69ef6f7165a7b057a0fd433ed180af76723f9bb5e1576a82",
      "pinned_source_sha256": "6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-student-20261001/pins/final-SC-real-51200 && CUDA_VISIBLE_DEVICES=3 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.evaluate_wuji_student_batch --teacher runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth --models SC-real-51200=runs/unified-student-20261001/SC-real-51200/step_051200.pth --states research/unified-student-20261001/data/final-all.npy --output runs/unified-student-20261001/final-SC-real-51200"
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
  "next": "Include this original failure evidence alongside the fixed four-source rendered comparison",
  "last_event": {
    "utc": "2026-10-01T19:32:29.169946+00:00",
    "event": "frozen_primary_failure_trace_video_verified",
    "evidence": "delivery/unified-student-20261001/student-original-failure-trace.json",
    "video_sha256": "f14cb12a2124bb8714691c3a0f3d2202ee5acf8be5498741890bb677f141ff82",
    "next": "Include this original failure evidence alongside the fixed four-source rendered comparison"
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
    "last_pushed_commit": "624e306b7318795557bac8457a46d57d9c1730cb",
    "release_id": 400860039,
    "tag": "wuji-unified-student-20261001-v1",
    "draft": true,
    "uploaded_assets": 18,
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
      "research/unified-student-20261001/upload-source64000.json"
    ],
    "teacher_paired_video": "delivery/unified-student-20261001/teacher-paired-four-sources.mp4",
    "student_video_pending": true,
    "final_cohort_opened": true
  },
  "verification_helpers": [
    "scripts/audit_wuji_student_final.py",
    "scripts/verify_wuji_student_public.py"
  ],
  "ordinary_training_endpoint": 70400,
  "final_freeze_sha256": "b2ec866146bd958501e41713f9db172f65edf079cafbb0f6267fe390b87fba80",
  "training_active_runs": []
}
```
