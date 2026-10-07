# Wuji 完整平放桌面取刀 → 连续推动当前 Goal

先读 `/data/research/artgym-experiments-20260921/flat-table-20261006/research/flat-table-20261006/CONTINUATION.md`。

```json
{
  "local_root": "/data/research/artgym-experiments-20260921/flat-table-20261006",
  "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
  "flat_table_pickup": true,
  "continuous_pickup_to_extension": false,
  "vision_validated": false,
  "real_robot_ran": false,
  "active_jobs": [],
  "next": "Upload exactsource/evidence v5 ascheckpoint while617 pathcontinues; thennativecurrentreaction",
  "last_event": {
    "utc": "2026-10-07T14:46:26.307224+00:00",
    "event": "C560_incremental_github_checkpoint_prepared",
    "evidence": [
      "delivery/wuji-direct-progress-20261007/v5",
      "delivery/wuji-direct-progress-20261007/v5/wuji-C560-R7-R8-incremental-evidence-20261007.tar.gz"
    ],
    "config": {
      "source_files": [
        "scripts/wuji_direct_pressure_path_servo.py",
        "scripts/wuji_direct_rolling_pair_clearance.py",
        "scripts/wuji_direct_grip_roll_servo.py",
        "scripts/wuji_direct_material_carrier.py",
        "scripts/prepare_wuji_acquired_thumb_stroke.py",
        "scripts/prepare_wuji_direct_sliding_stroke.py",
        "scripts/prepare_wuji_loaded_coordinated_motor.py",
        "scripts/plan_wuji_direct_coordinated_stroke.py",
        "scripts/record_wuji_flat_table_event.py"
      ],
      "evidence_files": 162,
      "goal_complete": false,
      "candidate": "C560-R8",
      "private_media_included": false,
      "native_617_continues": true
    },
    "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
    "source_sha256": {
      "scripts/run_g2_flat_table_demo.py": "8e164cbb10829bf5c93d1d7bb445196fcffc3d6c6b6e0e0a89b3f54afcb592aa",
      "scripts/run_wuji_flat_connected.py": "ce46b2900dc8d76e320e5198c4725ae150fc7f34e74737a318af7df05e4079fe",
      "scripts/prepare_wuji_relaxed_prefix.py": "bf1cb36e0e81a073f0ef02c0d9bb8a1086a54f783f7c88cbaf3d6b00feee3e10",
      "scripts/wuji_prefix_pose_adaptation.py": "b631fa93639741aea4f167d2bd6724b9e70abfc56833f24e8467fa9d2196a058",
      "scripts/wuji_direct_pickup.py": "cd018d2e6732603c026aa2b6d4d78aefeca7ac9738b251ffb33b7ded3b0cfb61",
      "scripts/wuji_direct_route.py": "8e967829c26970b4d50e5555dd9251528cc404c5391df6a9e4fbe88795de4d0f",
      "scripts/g2_kinematics.py": "8aba9ac3a73f43473306c59a6c4f8695ae65c3b32c47254e38486bf2e8a4f7e0",
      "scripts/g2_contact_geometry.py": "731467ee811b4dab8f8e80982ce4c2cf8962149ba25b6609a74cf9f4b2a76192",
      "scripts/wuji_direct_pressure_path_servo.py": "ed1469392096798bbe902898d952a814c151951452cdba67cb14b30ccfbaec2a",
      "scripts/wuji_direct_grip_roll_servo.py": "60e46e0586b0db5074d0f0e53b50b879bb6bbb621838515de13d1b9bc5949c96",
      "scripts/wuji_direct_live_ring.py": "f8ddeb7f8d30344c221b0f413772b8e0d9361742dc129b29dfd55aa6d1d4e58a",
      "scripts/wuji_direct_thumb_servo.py": "d2f550dd6634563fe9e77039cbdc7b7e9c9cb2a97f083939843105f304b47f90",
      "scripts/run_wuji_direct_connected.py": "dbf15e5d970fea9550395640c7f599767b4f0704a7deff8ce0427d955fac9a71",
      "scripts/run_wuji_direct_recorded.py": "10005ead81779fff465c33317564c787682bb94a47c9f8e292b86a613520fff2",
      "scripts/prepare_wuji_direct_actual_approach.py": "c6701ab781999c8cc9268fa27efaec8ae4b7c21912c9e36b04c534e773966491",
      "scripts/plan_wuji_direct_back_support.py": "5936ea115c9fa88d03399bf1a2f3dd0851407c206e958b9adaf992047db4338c",
      "scripts/wuji_direct_material_carrier.py": "ac5f4e2fc6c89408b755dd2ea82f6b01d66f8ddae9c31a642a558714f035c786",
      "scripts/wuji_direct_rolling_pair_clearance.py": "794fb77bee71b92ca713c489820483227f569d857079ec641cd806ac8810749c",
      "scripts/wuji_direct_joint_path_tracking.py": "5762bcf22c1cf64cdd2b6925c96ac7e9973ba94818d686188635ebf8cd1e1947",
      "scripts/time_wuji_free_thumb_path.py": "f91ca3e66aa206205796fcb36a6a9ddd866a7dd5a6872b7c7cced8b9066e6124",
      "scripts/prepare_wuji_base_first_thumb_path.py": "af61935195ec98b9035b5ddd357210ea6a908afcae2fb0ba93ab88e30d6af9b4",
      "scripts/prepare_wuji_acquired_thumb_stroke.py": "53e89d82996109b44bea61f0ef1c6c2a435b6d91f2c027101fbcc59d489e4261",
      "scripts/prepare_wuji_direct_sliding_stroke.py": "4e2089dec05c03753d18b662a90f812de706bab966ca8a5b034094672e173b0a",
      "scripts/prepare_wuji_loaded_coordinated_motor.py": "39283f4540fcd4e6f48f6a96bb4f63275c4c4e4d47891751d900a14c6aeb80a6",
      "scripts/plan_wuji_direct_coordinated_stroke.py": "4ff33c2d384788dcd7a58e2b87389831f90160f9cb70d617af1e49c9bf7bd1c9"
    },
    "next": "Upload exactsource/evidence v5 ascheckpoint while617 pathcontinues; thennativecurrentreaction"
  },
  "remote_root": "/home/wangjiarui/artgym-newknife-20261005",
  "placement_generalization": "Sharedrule positive29.805mm/negative30.402mm repaired; knownconditions consumedlocalregression, notunseen",
  "geometry_load_generalization": "Finalsharedrule nominal1.25N22.497mm andmidjointcondition21.319mm, no percase pressureselection",
  "pose_source": "sim_oracle explicit pose interface and development prior contacts",
  "delivery_complete": false,
  "local_resource_monitor_pid": null,
  "resource_four_hour_compliance_claim": false,
  "goal_status": "active",
  "github_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-direct-progress-20261007-v4",
  "github_progress_source_commit": "c04cead0bf172135ececae5ea95058d28562d6c0",
  "github_commit": "c04cead0bf172135ececae5ea95058d28562d6c0",
  "all_saved_progress_published": false,
  "execution_priority": "Fastest reproducible continuous demo; uncertainty-driven minimal experiments; reuse actual A state/history; no homogeneous failures or premature matrices",
  "execution_limitation_scope": "Blocked content may not be reproduced/worked around; specific rejected operation and trigger absent from original notice. No blanket simulation prohibition established.",
  "recorded_actual_hold_1s": true,
  "generalization_complete": false,
  "action_quality_accepted": false,
  "action_quality_scope": "Internal simulation checks with disclosedvisualsampling/exclusions; externaluser/hardwareacceptancefalse",
  "necessary_generalization_resolved": false,
  "goal_complete": false,
  "github_branch": "feat/wuji-flat-table-20261006",
  "simulation_requested_scope_complete": false,
  "external_user_acceptance": false,
  "axial_force_measurement_resolved": false,
  "direct_pickup_goal": true,
  "direct_pickup_complete": true,
  "direct_pickup_generalization_complete": false,
  "direct_stage": "C560-R7 currentflatnormal cap+measuredThumbreserve -> actualstroke",
  "direct_flip_complete": true,
  "direct_push_complete": false,
  "legacy_baseline": {
    "continuous_pickup_to_extension": true,
    "local_five_checks_passed": true,
    "direct_goal8_success": false
  },
  "direct_short_push_complete": true,
  "direct_current_safe_pickup_complete": false,
  "direct_current_safe_flip_complete": true,
  "direct_current_safe_push_complete": false
}
```

<!-- WUJI_FLAT_TABLE_HISTORY -->
# Wuji 单次伸出 >20mm 当前Goal

先读 `/data/research/artgym-experiments-20260921/contact-transfer-20261006/research/contact-transfer-20261006/CONTINUATION.md`。保留 singlepush 1.25 N 基线；映射、力矩、接触适配和部署准备。

```json
{
  "started_utc": "2026-10-05T16:15:13.199645+00:00",
  "local_root": "/data/research/artgym-experiments-20260921/contact-transfer-20261006",
  "baseline_local_commit": "df7a3240c92b2d2c771d3981b4be1d012190f4c9",
  "baseline_github_commit": "cae68dbda71dcb31954d34bd669394e445a2ccc4",
  "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
  "phase": "Implemented, independently verified and publicly delivered; upper geometry coordination and real calibration remain",
  "real_robot_ran": false,
  "delivery_complete": true,
  "next": "本轮交付已完成，无本轮计算任务。真机续接须核实 G2 右臂及 Wuji 一代右手连接、轴向/零点/限位/电流及控制响应，并开展同握姿法向与轴向分离测力、有效推力保持至少 1 秒。若继续仿真，针对大尺寸支撑与滚转协调选择新机制或有依据的专项训练；不重复成功测试或增益扫描，不把阻抗目标当作实际握姿。",
  "last_event": {
    "utc": "2026-10-05T16:57:31.979026+00:00",
    "event": "final_public_source_head_and_handoff_verified",
    "evidence": [
      "research/contact-transfer-20261006/PUBLIC-DELIVERY-RECEIPT.json",
      "research/contact-transfer-20261006/PUBLIC-DOWNLOAD-VERIFICATION.json"
    ],
    "config": {
      "final_branch_github_commit": "d2124cb0d98db5c4c97a71d8492733c7cb4642c0",
      "release_source_tag_commit": "3b0ffc4eae9bce257af6e03cd20265763ad0fc34",
      "server_digest_verified_assets": 37,
      "complete_videos": 24,
      "anonymous_downloads_verified": 2
    },
    "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
    "next": "本轮交付已完成，无本轮计算任务。真机续接须核实 G2 右臂及 Wuji 一代右手连接、轴向/零点/限位/电流及控制响应，并开展同握姿法向与轴向分离测力、有效推力保持至少 1 秒。若继续仿真，针对大尺寸支撑与滚转协调选择新机制或有依据的专项训练；不重复成功测试或增益扫描，不把阻抗目标当作实际握姿。"
  },
  "mapping_verified": true,
  "hardware_load_model_status": "Independent virtual work and signed contributions verified; corrected worst38.79% URDF model, not hardware reserve",
  "device_interface_verified": "InstalledSDK1.8, actual signatures and HandAPI fixture passed; no device connection",
  "necessary_generalization_status": "Near-small34mm physically29.71mm; actual corrected pose20s11.8mm clear. Target-only projection is conservative ablation, not mandatory new task constraint. NEW mid1.25N+delay22.12mm passes; NEW upper3.49mm fails.",
  "extension_demo_ready": true,
  "force_margin_evidence": "Retained1.25N baseline exactly reproduces24.366mm; no newly validated higher capacity",
  "axial_force_measurement_status": "Native total axial contact force unavailable/null",
  "minimum_gpu_utilization_requirement": null,
  "gpu_hour_cap": null,
  "reproducible_restore_passed": true,
  "active_jobs": [],
  "github_branch": "feat/wuji-contact-transfer-20261006",
  "github_commit": "d2124cb0d98db5c4c97a71d8492733c7cb4642c0",
  "github_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-contact-transfer-20261006-v1",
  "release_source_commit": "3b0ffc4eae9bce257af6e03cd20265763ad0fc34",
  "goal_simulation_and_delivery_complete": true
}
```

<!-- WUJI_CONTACT_TRANSFER_HISTORY -->
# Wuji 单次伸出 >20mm 当前Goal

先读 `/data/research/artgym-experiments-20260921/singlepush-20261005/research/singlepush-20261005/CONTINUATION.md`。旧双循环不再是本轮要求。

```json
{
  "started_utc": "2026-10-05T14:51:31.280510+00:00",
  "local_root": "/data/research/artgym-experiments-20260921/singlepush-20261005",
  "baseline_local_commit": "0fb3073",
  "baseline_github_commit": "2e0fd042eae31eff0088958277282afee379cd0a",
  "phase": "Implementation, validation, complete videos and reproducible delivery complete; actual hardware/full-range gaps explicitly retained",
  "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
  "extension_demo_ready": true,
  "force_margin_evidence": "Original1.25N fails19.16mm; path-feedback1.25N passes24.90mm with continuous cap contact; demonstrated lower bound improved25% from1N to1.25N,1.5N remains19.87mm fail",
  "necessary_generalization_status": "Two NEW frozen joint passes (near-large28.53mm, shift-delay31.20mm), near-small35mm final-point selfcollision certificate rejected. Development small30.47mm/middle25.73mm pass; large cap contact failure retained.",
  "axial_force_measurement_status": "unavailable native total tangential channel; normal solver contribution only",
  "hardware_check_status": "Final actual trajectory offline composite check done: normalp05/mean/peak + axial.7355/1/1.25/1.5N + thumb gravity/dynamics within URDF effort, max44.24%; thumb4 reaches position bound; actual hardware stiffness/limits/forces unread; nonmoving measurement entry verified",
  "real_robot_ran": false,
  "delivery_complete": true,
  "active_jobs": [],
  "next": "If continuing toward real demo, measure actual limits/stiffness and sustained normal/axial output at start/middle/end of the same grasp; do not restart successful simulation or sweep gains",
  "last_event": {
    "utc": "2026-10-05T15:31:25.300577+00:00",
    "event": "anonymous_public_downloads_and_all_12_uncut_videos_verified",
    "evidence": "research/singlepush-20261005/PUBLIC-DOWNLOAD-VERIFICATION.json",
    "config": {
      "downloads": 2,
      "bundle_videos": 12,
      "server_assets_digest_verified": 26,
      "source_tag": "7205de11688b6e678a45839a79a92f6148a4c866"
    },
    "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
    "next": "If continuing toward real demo, measure actual limits/stiffness and sustained normal/axial output at start/middle/end of the same grasp; do not restart successful simulation or sweep gains"
  },
  "reproducible_restore_passed": true,
  "github_branch": "feat/wuji-singlepush-20261005",
  "github_commit": "7205de11688b6e678a45839a79a92f6148a4c866",
  "github_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-singlepush-20261005-v1",
  "release_source_commit": "7205de11688b6e678a45839a79a92f6148a4c866",
  "goal_simulation_and_delivery_complete": true
}
```

<!-- WUJI_SINGLEPUSH_HISTORY -->
# Wuji 高阻力双向操作当前轮

实际副本 `/data/research/artgym-experiments-20260921/highload-20261005`。先读 research/highload-20261005/{GOAL.md,STATE.json}。禁止子代理、真机动作、隐蔽或填充占卡；旧冻结结果不改。PID需重新核验。

```json
{
  "round_start_utc": "2026-10-05T09:46:38.983466+00:00",
  "phase": "Stage delivered: joint-condition travel improvement and full-task load bound; highload sustainability and hardware Goal unresolved",
  "local_root": "/data/research/artgym-experiments-20260921/highload-20261005",
  "remote_root": "/home/wangjiarui/artgym-highload-20261005",
  "baseline_local_commit": "5214b24d87744acc66d540d53f84eec3db3a7779",
  "baseline_github_commit": "fcf602a0afb6a531bcda4f63c64c8e01d6acdd65",
  "baseline_release": "wuji-g2-traction-20261005-v1",
  "actor_sha256": "ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a",
  "minimum_work_hours": 0,
  "gpu_hour_cap": null,
  "no_subagents": true,
  "real_robot_ran": false,
  "delivery_complete": true,
  "goal_complete": false,
  "active_jobs": [],
  "next": "本轮交付完成，无本轮计算在运行。继续时先读FINAL-REPORT与PUBLIC-DELIVERY-RECEIPT，保留V13基线、tracking1工程候选与.20+.05N能力证据；勿重跑已否决时序/重锚/支撑展开/压力方向消融。fresh01–04是开发，unseen05/06已消费为验证，不再称全新。高阻重复后承托/落座协调仍失效；下一项工作须有新机制或原刀阻力/有效闭合行程/SDK输入。原刀B/C与真机仍未完成，不自动发机器人指令。",
  "last_event": {
    "utc": "2026-10-05T10:27:25.836936+00:00",
    "event": "final_delivery_handoff",
    "evidence": [
      "research/highload-20261005/PUBLIC-DELIVERY-RECEIPT.json",
      "research/highload-20261005/FINAL-REPORT.md",
      "research/highload-20261005/REPRODUCE.md"
    ],
    "phase": "Stage delivered: joint-condition travel improvement and full-task load bound; highload sustainability and hardware Goal unresolved",
    "conclusion": "22 assets server SHA verified,3 anonymous downloads match,1069-file empty-directory capacity restore exact.31 new physical trials,6 full raw videos. Source and reusable negative interventions published; no new training or robot commands. Remote18.04% below26%, observed33min only.",
    "state_updates": {
      "delivery_complete": true,
      "functional_demo_ready": true,
      "new_candidate_original_score_pass": false,
      "necessary_generalization_resolved": false,
      "axial_force_measurement_resolved": false,
      "hardware_ready": false,
      "real_robot_ran": false,
      "goal_complete": false,
      "github_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-highload-20261005-v1",
      "resource_monitors_stopped": true,
      "active_jobs": [],
      "active_remote_launchers": [],
      "resource_four_hour_compliance_claim": false,
      "remote_observed_mean_percent": 18.043367346938776,
      "remote_observed_minutes": 33.026437334219615
    },
    "next": "本轮交付完成，无本轮计算在运行。继续时先读FINAL-REPORT与PUBLIC-DELIVERY-RECEIPT，保留V13基线、tracking1工程候选与.20+.05N能力证据；勿重跑已否决时序/重锚/支撑展开/压力方向消融。fresh01–04是开发，unseen05/06已消费为验证，不再称全新。高阻重复后承托/落座协调仍失效；下一项工作须有新机制或原刀阻力/有效闭合行程/SDK输入。原刀B/C与真机仍未完成，不自动发机器人指令。"
  },
  "local_resource_monitor_pid": null,
  "resource_monitors_stopped": true,
  "remote_resource_monitor_pid": null,
  "selected_manifest": "research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json",
  "new_candidate_original_score_pass": false,
  "functional_demo_ready": true,
  "necessary_generalization_resolved": false,
  "axial_force_measurement_resolved": false,
  "active_remote_launchers": [],
  "github_branch": "feat/wuji-highload-20261005",
  "github_commit": "8b3c5be732f63225157298ae9d559651ea7cbcc9",
  "hardware_ready": false,
  "github_release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-highload-20261005-v1",
  "resource_four_hour_compliance_claim": false,
  "remote_observed_mean_percent": 18.043367346938776,
  "remote_observed_minutes": 33.026437334219615
}
```
