# Wuji 抗转动功能抓姿当前轮

实际副本 `/data/research/artgym-experiments-20260921/antirotation-grasp-20261004`。先读 research/antirotation-grasp-20261004/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-03T20:03:23+00:00",
  "minimum_work_hours": 12,
  "earliest_12h_utc": "2026-10-04T08:03:23+00:00",
  "phase": "Full functional nominal V17 retained; common geometry through learned acquisition and necessary height preparation active",
  "baseline_local_commit": "b75e12effbfb5a9ce740411b5ec699db60338b3e",
  "baseline_github_commit": "d0d6ce01d5550ec5b512fdc4e510c5546569d8b4",
  "baseline_release": "wuji-g2-support-pressure-20261003-v1",
  "gpu_hour_cap": null,
  "gpu_utilization_rule": {
    "whole_machine_4h_floor_percent": 26,
    "running_target_above_percent": 40,
    "source": "CurrentAGENTS.md; usefulcomputationonly, no concealed/filler jobs"
  },
  "delivery_complete": false,
  "functional_demo_ready": true,
  "necessary_generalization_resolved": false,
  "hardware_ready": false,
  "real_robot_ran": false,
  "goal_complete": false,
  "active_jobs": [
    {
      "name": "strict16-table-prior-closure-longhorizon-range04-reset750-v8",
      "machine": "local",
      "pid": 1285622,
      "gpu": 0,
      "source_commit": "c810a636dfa155e2a9a25d6b283cd91154d19a60",
      "source_patch_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "source_sha256": {
        "scripts/wuji_initial_table_prior.py": "8c4f1a32ad2840c1e35fdd1f876402e443455ea1fc426356927d872754e506ae",
        "scripts/g2_continuous_scene.py": "7f6f214326a976815e796a93118277e79d0fbb3b4e6b88be285245b6b2f7094d",
        "scripts/g2_r800_policy.py": "de6a473fac5bb15f9e6f22c2ad4aa4e5b3c23399b263075621586fb0ebf0aa9a",
        "scripts/g2_batched_r800.py": "b4a476316840ed2b8008a1016baaab0a581989ffc1ad9ff12a26dfc96f7440f3",
        "scripts/wuji_known_controller.py": "3e4870ee35719db2f2dc8760d6b5c58a757c5b4ba944f27d2cb2e15533df4ad6",
        "scripts/wuji_bounded_motor_residual.py": "39ad6c94a39f5dd8d71a2e7a50d65eb973fe65078861913828f7913e77873635",
        "scripts/run_g2_robust_demo.py": "c39e8b535c7395708059b7fbc163467736d769cf2c2c159f17b5a3d3e6bdd3ef",
        "scripts/train_wuji_robust_residual.py": "059fa9f79fd29b75783c6e145d8cec89d1c317313fc4e032e174d04b8bd301f9"
      },
      "input_sha256": {
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/initial-geometry-v2/projected-00/reference-v1.json": "6008235b6499118f4a7a5841f9a0f5288d992418d182faf826f24f265236438c",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-table-prior-prefix-v2/scene16.json": "0c300bf407d987b6b11da38b4f2d3cec204afc494eeb37acd363650904fac766",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-learned-prefix-v1/schedule1024.json": "f4d62ab5ca19e92b9034f66d626edd7e3cfcd05ee95d264c0c2d9e0e454e9d93",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth": "11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-learned-prefix-v1/registry.json": "d00ecf6113fd9f92cd2735f673b36d6db78925a7163ab5c6b8a2e764ff8fa09c"
      },
      "start_utc": "2026-10-04T04:57:21.711422+00:00"
    },
    {
      "name": "strict16-table-prior-closure-longhorizon-range12-reset750-v9",
      "machine": "local",
      "pid": 1285623,
      "gpu": 0,
      "source_commit": "c810a636dfa155e2a9a25d6b283cd91154d19a60",
      "source_patch_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "source_sha256": {
        "scripts/wuji_initial_table_prior.py": "8c4f1a32ad2840c1e35fdd1f876402e443455ea1fc426356927d872754e506ae",
        "scripts/g2_continuous_scene.py": "7f6f214326a976815e796a93118277e79d0fbb3b4e6b88be285245b6b2f7094d",
        "scripts/g2_r800_policy.py": "de6a473fac5bb15f9e6f22c2ad4aa4e5b3c23399b263075621586fb0ebf0aa9a",
        "scripts/g2_batched_r800.py": "b4a476316840ed2b8008a1016baaab0a581989ffc1ad9ff12a26dfc96f7440f3",
        "scripts/wuji_known_controller.py": "3e4870ee35719db2f2dc8760d6b5c58a757c5b4ba944f27d2cb2e15533df4ad6",
        "scripts/wuji_bounded_motor_residual.py": "39ad6c94a39f5dd8d71a2e7a50d65eb973fe65078861913828f7913e77873635",
        "scripts/run_g2_robust_demo.py": "c39e8b535c7395708059b7fbc163467736d769cf2c2c159f17b5a3d3e6bdd3ef",
        "scripts/train_wuji_robust_residual.py": "059fa9f79fd29b75783c6e145d8cec89d1c317313fc4e032e174d04b8bd301f9"
      },
      "input_sha256": {
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/initial-geometry-v2/projected-00/reference-v1.json": "6008235b6499118f4a7a5841f9a0f5288d992418d182faf826f24f265236438c",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-table-prior-prefix-v2/scene16.json": "0c300bf407d987b6b11da38b4f2d3cec204afc494eeb37acd363650904fac766",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-learned-prefix-v1/schedule1024.json": "f4d62ab5ca19e92b9034f66d626edd7e3cfcd05ee95d264c0c2d9e0e454e9d93",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth": "11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d",
        "/data/research/artgym-experiments-20260921/antirotation-grasp-20261004/runs/antirotation-grasp-20261004/strict-geometry-learned-prefix-v1/registry.json": "d00ecf6113fd9f92cd2735f673b36d6db78925a7163ab5c6b8a2e764ff8fa09c"
      },
      "start_utc": "2026-10-04T04:57:21.727518+00:00"
    }
  ],
  "no_subagents": true,
  "remote_root": "/home/wangjiarui/artgym-antirotation-grasp-20261004",
  "private_attachment_media": "/tmp/wuji-antirotation-attachment-20261004",
  "next": "Finalize afterfresh4/materialresume andatleast12h, then publishnewRelease. Reviewcaptionframes alreadycomplete.",
  "last_event": {
    "utc": "2026-10-04T05:54:23.158827+00:00",
    "event": "browsable_report_preview_created",
    "config": {
      "final": false,
      "scope": "Embeddedactualframes, fouruncutdualviewvideo links, role-separateddevelopment/validation/hardware; Release links pendingpublicassets",
      "video_count": 4
    },
    "evidence": "runs/antirotation-grasp-20261004/presentation/report-preview.html",
    "next": "Finalize afterfresh4/materialresume andatleast12h, then publishnewRelease. Reviewcaptionframes alreadycomplete."
  },
  "resource_monitor_pid": 502,
  "resource_monitor_start_utc": "2026-10-03T20:15:18.833167+00:00",
  "held_bidirectional_development_ready": true,
  "github_branch": "feat/wuji-antirotation-grasp-20261004",
  "github_commit": "ceb51afb25e8c30de9061a25408cd6dfe03cc8c2",
  "local_scientific_commit": "9c975430dd8c60a86c4c5633c971398e0a62589b",
  "actual_table_integration_pipeline_pid": null,
  "lower_side_direct_pipeline_pid": null,
  "local_coordinate_comparison_pipeline_pid": null,
  "projected_noisy_nominal_pipeline_pid": null,
  "contact_normal_pipeline_pid": null,
  "functional_demo_scope": "Nominal/noisy initial estimate development case .2/.2 only; actual32/26mm extensions for40mmcommand, necessarygen unresolved",
  "common_geometry_bank16_pipeline_pid": null,
  "local_resource_monitor_pid": 1174078,
  "three_geometry_curriculum_pipeline_pid": null,
  "height_geometry_bank_pipeline_pid": null,
  "strict_geometry_learned_prefix_pipeline_pid": null,
  "fresh_joint_challenges_pipeline_pid": null,
  "joint_reserve_repair_pipeline_pid": null,
  "larger_support_newprefix_pipeline_pid": null,
  "correct_table_prior_prefix_pair_pipeline_pid": 1283870,
  "fresh_joint_validation_pipeline_pid": 1301102,
  "newprefix_recovery_pipeline_pid": 1307282,
  "height_development_four_pipeline_pid": null,
  "annotated_media_pipeline_pid": null
}
```
