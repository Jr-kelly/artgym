# 当前 Wuji 尺寸泛化 Goal

工作区 `/data/research/artgym-experiments-20260921/geometry-generalization-20261002`。先读 research/geometry-generalization-20261002/{GOAL.md,STATE.json,HANDOFF.md,PENDING_TASKS.md,DECISIONS.jsonl}。禁止子代理；旧最终集保持关闭。PID/利用率为带时间历史记录，须重新验证。旧墙钟截止及续训方案已由新Goal替换。

```json
{
  "start_utc": "2026-10-01T21:11:50.381254+00:00",
  "base_sha": "e6c9f3e0d6167b0df529a5e7d75c88b91ff42613",
  "max_gpu_hours": 64,
  "historical_gpu_hours": 32.4534053852823,
  "new_gpu_hours": 4.828895305924946,
  "cumulative_gpu_hours": 37.28230069120725,
  "remaining_gpu_hours": 26.717699308792753,
  "reserved_final_gpu_hours": 6,
  "max_concurrent_gpus": 4,
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-geometry-20261002",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "phase": "Independent final evaluation of retained frozen parents",
  "models": {
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
  },
  "goal_sha256": "9dafc220bfe1b1d3bbf1d6f7cfa21259bc8cff9410ff740156c24425365bdfb1",
  "active_jobs": [
    {
      "name": "final-L110-batch",
      "gpu": 3,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L110",
        "--static",
        "L110-static-final",
        "--split",
        "final-attempts",
        "--take",
        "128",
        "--prefix",
        "final-"
      ],
      "start_utc": "2026-10-01T22:51:30.775254+00:00",
      "local_pid": 1380189,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "registered_models": {
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
      },
      "local_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "pinned_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/final-L110-batch && CUDA_VISIBLE_DEVICES=3 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L110 --static L110-static-final --split final-attempts --take 128 --prefix final-"
    },
    {
      "name": "final-L90-batch",
      "gpu": 2,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L90",
        "--static",
        "L90-static-final",
        "--split",
        "final-attempts",
        "--take",
        "128",
        "--prefix",
        "final-"
      ],
      "start_utc": "2026-10-01T22:51:27.831412+00:00",
      "local_pid": 1380139,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "registered_models": {
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
      },
      "local_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "pinned_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/final-L90-batch && CUDA_VISIBLE_DEVICES=2 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L90 --static L90-static-final --split final-attempts --take 128 --prefix final-"
    },
    {
      "name": "final-baseline-batch",
      "gpu": 0,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "baseline",
        "--static",
        "baseline-static-final",
        "--split",
        "final-attempts",
        "--take",
        "128",
        "--prefix",
        "final-"
      ],
      "start_utc": "2026-10-01T22:51:21.473746+00:00",
      "local_pid": 1380036,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "registered_models": {
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
      },
      "local_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "pinned_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/final-baseline-batch && CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label baseline --static baseline-static-final --split final-attempts --take 128 --prefix final-"
    },
    {
      "name": "final-L80-batch",
      "gpu": 1,
      "seconds": 1800,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L80",
        "--static",
        "L80-static-final",
        "--split",
        "final-attempts",
        "--take",
        "128",
        "--prefix",
        "final-"
      ],
      "start_utc": "2026-10-01T22:51:24.743945+00:00",
      "local_pid": 1380097,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": true,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "registered_models": {
        "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
        "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
      },
      "local_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "pinned_source_sha256": "0413cd7b5237d039be75575fe5c820a6dfde50c41a4746f556709d0b0cb25d62",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/final-L80-batch && CUDA_VISIBLE_DEVICES=1 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1800 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L80 --static L80-static-final --split final-attempts --take 128 --prefix final-"
    }
  ],
  "final_opened": true,
  "next": "Restore-check and upload; local originals retained",
  "last_event": {
    "utc": "2026-10-01T22:58:43.384563+00:00",
    "event": "archive_completed",
    "name": "geometry-confirm64-T120",
    "archive": "delivery/geometry-generalization-20261002/geometry-confirm64-T120.tar.gz",
    "sha256": "e589d2c3f72b1b8def2856e48bd3bd1dfd0aad7d96b694f52124dcbf0e1d664b",
    "size": 360962261,
    "files": 24,
    "next": "Restore-check and upload; local originals retained"
  },
  "active_gpu_elapsed_hours": 0.48575549416666663,
  "cumulative_gpu_hours_including_active": 37.768056185373915,
  "remaining_including_active": 26.231943814626085,
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
  "final_freeze_sha256": "d986f2f17450192a7b44e8bf044496a88db62597ad0d1b65acc48a981dc28f32"
}
```
