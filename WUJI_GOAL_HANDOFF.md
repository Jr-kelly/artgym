# Wuji 包覆承托与轴向测力当前轮

实际副本 `/data/research/artgym-experiments-20260921/wrap-force-20261004`。先读 research/wrap-force-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-04T10:51:40.525679+00:00",
  "minimum_work_hours": 12,
  "minimum_finish_utc": "2026-10-04T22:51:40.525679+00:00",
  "phase": "Implement axial measurement and functional wrap candidates",
  "baseline_release": "wuji-g2-antirotation-grasp-20261004-v1",
  "baseline_local_commit": "29825ad91b7075b080f96e65370f49a0201c614b",
  "baseline_github_commit": "b892d8909efb9da33407b02e6ffd229f7d6f00b4",
  "baseline_tag_commit": "59eb7833c565b857a28f5016a7b11dc8e2eb013e",
  "gpu_hour_cap": null,
  "no_subagents": true,
  "no_real_robot_commands": true,
  "delivery_complete": false,
  "functional_demo_ready": false,
  "necessary_generalization_resolved": false,
  "hardware_ready": false,
  "real_robot_ran": false,
  "goal_complete": false,
  "axial_force_measurement_resolved": false,
  "active_jobs": [
    {
      "name": "source1-lateral-acquisition-v1",
      "machine": "local",
      "pid": 3365305,
      "gpu": 0,
      "source_commit": "cd87426d322a790d36237b634fc2d2027a8a2b0d",
      "source_patch_sha256": "d1b6bfb3f96fa813ebde51f026d8d5d593202bdd5b56c1d501fd0e5d8c75aff1",
      "source_sha256": {
        "scripts/wuji_initial_table_prior.py": "8c4f1a32ad2840c1e35fdd1f876402e443455ea1fc426356927d872754e506ae",
        "scripts/wuji_joint_deflection_acquisition.py": "9ed522a0d370e344b6ab4e2595ddc0e6b1b8a8dc18f4512c6f4654b7623777b5",
        "scripts/wuji_known_acquisition_prefix.py": "17c2a2706f5f29f5167a223464cb0c67dea43800b7fdc70df2453ad98ccb2d03",
        "scripts/replay_wuji_support_commands.py": "f29eafff174bc92b1ad2a4c1a4a367fbc50ca1f7ff35a32571406472e3fa37c2",
        "scripts/export_wuji_legal_replay.py": "0df6f22cd86ba7794a14cfb5f180ffe717ed62869828bf08fa7c15c35162c26b",
        "scripts/g2_continuous_scene.py": "7f6f214326a976815e796a93118277e79d0fbb3b4e6b88be285245b6b2f7094d",
        "scripts/g2_r800_policy.py": "de6a473fac5bb15f9e6f22c2ad4aa4e5b3c23399b263075621586fb0ebf0aa9a",
        "scripts/g2_batched_r800.py": "b4a476316840ed2b8008a1016baaab0a581989ffc1ad9ff12a26dfc96f7440f3",
        "scripts/wuji_known_controller.py": "3e4870ee35719db2f2dc8760d6b5c58a757c5b4ba944f27d2cb2e15533df4ad6",
        "scripts/wuji_bounded_motor_residual.py": "39ad6c94a39f5dd8d71a2e7a50d65eb973fe65078861913828f7913e77873635",
        "scripts/run_g2_robust_demo.py": "26a95d754e6b3a573054cfd29828a06902a2d86551501a7fd575aa8370a807b8",
        "scripts/train_wuji_robust_residual.py": "8c8aa5ebe4ed958e99010adf963fa3087a234046839c9e1eba41802e1cb94649",
        "scripts/plan_g2_functional_acquisition_path.py": "cc5ee46db727a2f0ca2efe0854e28921bdf1fdf0d9d8f6c6862a69f851deec14"
      },
      "input_sha256": {
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/motor-plan.json": "235a0a4dd014055915d28d551d6a962aaffaaf36083cd279f8ab19cf21769bdd",
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/localization.json": "4cb1d1d5e2f86ff528225ffab6fcb48d071fc12c61bea6338a0b49b226a39856"
      },
      "start_utc": "2026-10-04T12:16:23.946176+00:00"
    }
  ],
  "remote_gpu_inventory": {
    "verified_utc": "2026-10-04T10:51:40.525679+00:00",
    "count": 4,
    "name": "NVIDIA H200",
    "initially_idle": true
  },
  "next": "Inspect actual result and persist conclusion; no simulation/hardware success inferred from process startup",
  "last_event": {
    "utc": "2026-10-04T12:16:23.946389+00:00",
    "event": "wrap_force_job_started",
    "active_job": {
      "name": "source1-lateral-acquisition-v1",
      "machine": "local",
      "pid": 3365305,
      "gpu": 0,
      "source_commit": "cd87426d322a790d36237b634fc2d2027a8a2b0d",
      "source_patch_sha256": "d1b6bfb3f96fa813ebde51f026d8d5d593202bdd5b56c1d501fd0e5d8c75aff1",
      "source_sha256": {
        "scripts/wuji_initial_table_prior.py": "8c4f1a32ad2840c1e35fdd1f876402e443455ea1fc426356927d872754e506ae",
        "scripts/wuji_joint_deflection_acquisition.py": "9ed522a0d370e344b6ab4e2595ddc0e6b1b8a8dc18f4512c6f4654b7623777b5",
        "scripts/wuji_known_acquisition_prefix.py": "17c2a2706f5f29f5167a223464cb0c67dea43800b7fdc70df2453ad98ccb2d03",
        "scripts/replay_wuji_support_commands.py": "f29eafff174bc92b1ad2a4c1a4a367fbc50ca1f7ff35a32571406472e3fa37c2",
        "scripts/export_wuji_legal_replay.py": "0df6f22cd86ba7794a14cfb5f180ffe717ed62869828bf08fa7c15c35162c26b",
        "scripts/g2_continuous_scene.py": "7f6f214326a976815e796a93118277e79d0fbb3b4e6b88be285245b6b2f7094d",
        "scripts/g2_r800_policy.py": "de6a473fac5bb15f9e6f22c2ad4aa4e5b3c23399b263075621586fb0ebf0aa9a",
        "scripts/g2_batched_r800.py": "b4a476316840ed2b8008a1016baaab0a581989ffc1ad9ff12a26dfc96f7440f3",
        "scripts/wuji_known_controller.py": "3e4870ee35719db2f2dc8760d6b5c58a757c5b4ba944f27d2cb2e15533df4ad6",
        "scripts/wuji_bounded_motor_residual.py": "39ad6c94a39f5dd8d71a2e7a50d65eb973fe65078861913828f7913e77873635",
        "scripts/run_g2_robust_demo.py": "26a95d754e6b3a573054cfd29828a06902a2d86551501a7fd575aa8370a807b8",
        "scripts/train_wuji_robust_residual.py": "8c8aa5ebe4ed958e99010adf963fa3087a234046839c9e1eba41802e1cb94649",
        "scripts/plan_g2_functional_acquisition_path.py": "cc5ee46db727a2f0ca2efe0854e28921bdf1fdf0d9d8f6c6862a69f851deec14"
      },
      "input_sha256": {
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/motor-plan.json": "235a0a4dd014055915d28d551d6a962aaffaaf36083cd279f8ab19cf21769bdd",
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/localization.json": "4cb1d1d5e2f86ff528225ffab6fcb48d071fc12c61bea6338a0b49b226a39856"
      },
      "start_utc": "2026-10-04T12:16:23.946176+00:00"
    },
    "config": {
      "command": [
        "/home/agiuser/miniconda3/envs/artgym/bin/python",
        "-m",
        "scripts.plan_g2_functional_acquisition_path",
        "--plan",
        "runs/wrap-force-20261004/comparison/four-sources-v1/source1/motor-plan.json",
        "--localization",
        "runs/wrap-force-20261004/comparison/four-sources-v1/source1/localization.json",
        "--lift",
        ".16",
        "--output",
        "runs/wrap-force-20261004/comparison/four-sources-v1/source1/lateral-acquisition"
      ],
      "pid": 3365305,
      "launcher_pid": 3365275,
      "gpu": 0,
      "source_commit": "cd87426d322a790d36237b634fc2d2027a8a2b0d",
      "source_patch_sha256": "d1b6bfb3f96fa813ebde51f026d8d5d593202bdd5b56c1d501fd0e5d8c75aff1",
      "source_sha256": {
        "scripts/wuji_initial_table_prior.py": "8c4f1a32ad2840c1e35fdd1f876402e443455ea1fc426356927d872754e506ae",
        "scripts/wuji_joint_deflection_acquisition.py": "9ed522a0d370e344b6ab4e2595ddc0e6b1b8a8dc18f4512c6f4654b7623777b5",
        "scripts/wuji_known_acquisition_prefix.py": "17c2a2706f5f29f5167a223464cb0c67dea43800b7fdc70df2453ad98ccb2d03",
        "scripts/replay_wuji_support_commands.py": "f29eafff174bc92b1ad2a4c1a4a367fbc50ca1f7ff35a32571406472e3fa37c2",
        "scripts/export_wuji_legal_replay.py": "0df6f22cd86ba7794a14cfb5f180ffe717ed62869828bf08fa7c15c35162c26b",
        "scripts/g2_continuous_scene.py": "7f6f214326a976815e796a93118277e79d0fbb3b4e6b88be285245b6b2f7094d",
        "scripts/g2_r800_policy.py": "de6a473fac5bb15f9e6f22c2ad4aa4e5b3c23399b263075621586fb0ebf0aa9a",
        "scripts/g2_batched_r800.py": "b4a476316840ed2b8008a1016baaab0a581989ffc1ad9ff12a26dfc96f7440f3",
        "scripts/wuji_known_controller.py": "3e4870ee35719db2f2dc8760d6b5c58a757c5b4ba944f27d2cb2e15533df4ad6",
        "scripts/wuji_bounded_motor_residual.py": "39ad6c94a39f5dd8d71a2e7a50d65eb973fe65078861913828f7913e77873635",
        "scripts/run_g2_robust_demo.py": "26a95d754e6b3a573054cfd29828a06902a2d86551501a7fd575aa8370a807b8",
        "scripts/train_wuji_robust_residual.py": "8c8aa5ebe4ed958e99010adf963fa3087a234046839c9e1eba41802e1cb94649",
        "scripts/plan_g2_functional_acquisition_path.py": "cc5ee46db727a2f0ca2efe0854e28921bdf1fdf0d9d8f6c6862a69f851deec14"
      },
      "input_sha256": {
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/motor-plan.json": "235a0a4dd014055915d28d551d6a962aaffaaf36083cd279f8ab19cf21769bdd",
        "/data/research/artgym-experiments-20260921/wrap-force-20261004/runs/wrap-force-20261004/comparison/four-sources-v1/source1/localization.json": "4cb1d1d5e2f86ff528225ffab6fcb48d071fc12c61bea6338a0b49b226a39856"
      },
      "start_utc": "2026-10-04T12:16:23.946176+00:00"
    },
    "evidence": "runs/wrap-force-20261004/jobs/source1-lateral-acquisition-v1",
    "next": "Inspect actual result and persist conclusion; no simulation/hardware success inferred from process startup"
  },
  "baseline_functional_demo_ready": true,
  "local_resource_monitor_pid": 3068820,
  "github_branch": "feat/wuji-wrap-force-20261004",
  "github_commit": "b37081889624869dcfe2bc723a15a37db4fd1c99",
  "local_scientific_commit": "cd87426d322a790d36237b634fc2d2027a8a2b0d",
  "multigrasp_comparison_required_before_long_training": true,
  "multigrasp_comparison_completed": false,
  "geometry_split_preserved": {
    "train": "000–011",
    "heldout": "012–015"
  },
  "endpoint_reference": "position above rail lower stop, not returned distance"
}
```
