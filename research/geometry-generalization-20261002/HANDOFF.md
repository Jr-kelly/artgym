# 当前 Wuji 尺寸泛化 Goal

工作区 `/data/research/artgym-experiments-20260921/geometry-generalization-20261002`。先读 research/geometry-generalization-20261002/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。禁止子代理；旧最终集保持关闭。PID/利用率为带时间历史记录，须重新验证。旧墙钟截止及续训方案已由新Goal替换。

```json
{
  "start_utc": "2026-10-01T21:11:50.381254+00:00",
  "base_sha": "e6c9f3e0d6167b0df529a5e7d75c88b91ff42613",
  "max_gpu_hours": 64,
  "historical_gpu_hours": 32.4534053852823,
  "new_gpu_hours": 0.14146861612796785,
  "cumulative_gpu_hours": 32.59487400141027,
  "remaining_gpu_hours": 31.40512599858973,
  "reserved_final_gpu_hours": 6,
  "max_concurrent_gpus": 4,
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "remote_root": "/tmp/artgym-geometry-20261002",
  "runtime": "/tmp/wuji-student-runtime/bin/python",
  "phase": "Frozen 13-condition paired capability screen",
  "models": {
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
  },
  "goal_sha256": "9dafc220bfe1b1d3bbf1d6f7cfa21259bc8cff9410ff740156c24425365bdfb1",
  "active_jobs": [
    {
      "name": "frozen-screen-baseline",
      "gpu": 0,
      "seconds": 1200,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "baseline",
        "--static",
        "baseline-static-screen-v2",
        "--skip",
        "teacher-S2",
        "student-S2"
      ],
      "start_utc": "2026-10-01T21:21:14.713915+00:00",
      "local_pid": 1309791,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "pinned_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/frozen-screen-baseline && CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1200 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label baseline --static baseline-static-screen-v2 --skip teacher-S2 student-S2"
    },
    {
      "name": "frozen-screen-L80",
      "gpu": 1,
      "seconds": 1200,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L80",
        "--static",
        "L80-static-fixed"
      ],
      "start_utc": "2026-10-01T21:21:15.636434+00:00",
      "local_pid": 1309799,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "pinned_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/frozen-screen-L80 && CUDA_VISIBLE_DEVICES=1 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1200 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L80 --static L80-static-fixed"
    },
    {
      "name": "frozen-screen-L90",
      "gpu": 2,
      "seconds": 1200,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L90",
        "--static",
        "L90-static-fixed"
      ],
      "start_utc": "2026-10-01T21:21:13.893104+00:00",
      "local_pid": 1309773,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "pinned_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/frozen-screen-L90 && CUDA_VISIBLE_DEVICES=2 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1200 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L90 --static L90-static-fixed"
    },
    {
      "name": "frozen-screen-L110",
      "gpu": 3,
      "seconds": 1200,
      "command": [
        "/tmp/wuji-student-runtime/bin/python",
        "-m",
        "scripts.batch_wuji_geometry",
        "--label",
        "L110",
        "--static",
        "L110-static-fixed"
      ],
      "start_utc": "2026-10-01T21:21:12.968165+00:00",
      "local_pid": 1309772,
      "remote_root": "/tmp/artgym-geometry-20261002",
      "final": false,
      "local": false,
      "resource_check": "0, 0\n1, 0\n2, 0\n3, 0\n",
      "local_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "pinned_source_sha256": "a93167189625c10996edffcf2589cfa816937f0e80bacf740de00ce1050658ae",
      "selected_source_sha256": {
        "scripts/evaluate_wuji_recovery.py": "9feaaac6e172ba6505277f2ffbaf9e3d2cbaa25dcdac52df1a14087de36d3ab5",
        "scripts/train_wuji_unified_student.py": "9e3932aa0c848728ec54c81ef28d779e45c1f6ba35751554e9b4403c4f846bf9",
        "scripts/wuji_known_controller.py": "b663ccb9c154a0c448935b4898c708cc506e7d42f4fb378c53607268142386d8",
        "scripts/wuji_student_interface.py": "78166ac137dbe432b7e000645a10a43981edc38b940283b6e4f1eaf28e6ca6a0",
        "isaacgymenvs/learning/a2c_sapg_priv_network_builder.py": "ecd00cc0fe90b313e0a2a9434be4f4fea8a2c079c755fad807caeb3cbcd9095e"
      },
      "pinned_source_matches_local": true,
      "remote_shell": "cd /tmp/artgym-geometry-20261002/pins/frozen-screen-L110 && CUDA_VISIBLE_DEVICES=3 LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 timeout --signal=TERM --kill-after=30 1200 /tmp/wuji-student-runtime/bin/python -m scripts.batch_wuji_geometry --label L110 --static L110-static-fixed"
    }
  ],
  "final_opened": false,
  "next": "Core GPUscreen continues; preserve separate self-stream numerical diagnostic, then confirm influential geometry/source conditions",
  "last_event": {
    "utc": "2026-10-01T21:27:07.343386+00:00",
    "event": "offline_reset_step_original_player_parity_verified",
    "evidence": "research/geometry-generalization-20261002/offline-runtime-audit.json",
    "result": {
      "passed": true,
      "steps": 80,
      "batch": 4,
      "dimensions": [
        "baseline",
        "T90",
        "W120"
      ],
      "nonconstant_joint_inputs": true,
      "partial_resets": [
        {
          "step": 17,
          "ids": [
            1,
            3
          ],
          "untouched_rnn_exact": true
        },
        {
          "step": 41,
          "ids": [
            0,
            2
          ],
          "untouched_rnn_exact": true
        }
      ],
      "max_absolute_errors": {
        "public": 4.470348358154297e-07,
        "history": 4.470348358154297e-07,
        "action": 1.138448715209961e-05,
        "target": 4.76837158203125e-07,
        "rnn": 0.00015076994895935059
      },
      "reference": "Original build_policy_player/get_action + ArtManip history update + inherited WujiDemoAligned/ArtManip pre_physics_step with no-hardware output stub",
      "models": {
        "teacher": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
        "student": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
      },
      "initial_data_sha256": {
        "baseline": "fccb3b4d66291e078ac4247fa3310ff780543a73982007767e4aad820ad3a506",
        "T90": "f5b9cd4681b618c3ed8da3b2041ee0c1e5b48eaad093f445f6e718b0a2dd9083",
        "W120": "b6e0ed4f8af55d656adbeca70be1ee2452ee9f2d0cc5be6ef8cd9d4845907a6c"
      },
      "scope": "CPU legal input replay/parity, not physical rollout or hardware. Commands external. Runtime accepts initial calibration and known geometry; no current object/slider/contact truth."
    },
    "next": "Core GPUscreen continues; preserve separate self-stream numerical diagnostic, then confirm influential geometry/source conditions"
  }
}
```
