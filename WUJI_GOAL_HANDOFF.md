# Wuji 单次伸出 >20mm 当前Goal

先读 `/data/research/artgym-experiments-20260921/contact-transfer-20261006/research/contact-transfer-20261006/CONTINUATION.md`。保留 singlepush 1.25 N 基线；映射、力矩、接触适配和部署准备。

```json
{
  "started_utc": "2026-10-05T16:15:13.199645+00:00",
  "local_root": "/data/research/artgym-experiments-20260921/contact-transfer-20261006",
  "baseline_local_commit": "df7a3240c92b2d2c771d3981b4be1d012190f4c9",
  "baseline_github_commit": "cae68dbda71dcb31954d34bd669394e445a2ccc4",
  "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
  "phase": "Implementation and validation complete; packaging fresh videos and reproducible delivery",
  "real_robot_ran": false,
  "delivery_complete": false,
  "next": "Publish exact source branch/tag and verify fresh Release/video downloads; no remaining useful jobs launched",
  "last_event": {
    "utc": "2026-10-05T16:45:44.432060+00:00",
    "event": "isolated_small_overlay_representative_restore_passed",
    "evidence": [
      "research/contact-transfer-20261006/RESTORE-VERIFICATION.json"
    ],
    "config": {
      "overlay_sha256": "b7f27569368055ae3b8596acb10c80789ffb055ed59c125db1733275e5b09adb",
      "verified_files": 2360,
      "active_forward_mm": 24.36626224880456,
      "trace_sha256": "d7ed4f78dbced95a8ddc0d0e36ddf8522767821ac6f8a428d82ea8b3cd7db3c8",
      "exact_match": true
    },
    "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
    "next": "Publish exact source branch/tag and verify fresh Release/video downloads; no remaining useful jobs launched"
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
  "active_jobs": []
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
