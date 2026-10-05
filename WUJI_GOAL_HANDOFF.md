# Wuji 单次伸出 >20mm 当前Goal

先读 `/data/research/artgym-experiments-20260921/singlepush-20261005/research/singlepush-20261005/CONTINUATION.md`。旧双循环不再是本轮要求。

```json
{
  "started_utc": "2026-10-05T14:51:31.280510+00:00",
  "local_root": "/data/research/artgym-experiments-20260921/singlepush-20261005",
  "baseline_local_commit": "0fb3073",
  "baseline_github_commit": "2e0fd042eae31eff0088958277282afee379cd0a",
  "phase": "Final implementation/validation/video complete; publishing reproducible GitHub delivery",
  "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
  "extension_demo_ready": true,
  "force_margin_evidence": "Original1.25N fails19.16mm; path-feedback1.25N passes24.90mm with continuous cap contact; demonstrated lower bound improved25% from1N to1.25N,1.5N remains19.87mm fail",
  "necessary_generalization_status": "Two NEW frozen joint passes (near-large28.53mm, shift-delay31.20mm), near-small35mm final-point selfcollision certificate rejected. Development small30.47mm/middle25.73mm pass; large cap contact failure retained.",
  "axial_force_measurement_status": "unavailable native total tangential channel; normal solver contribution only",
  "hardware_check_status": "Final actual trajectory offline composite check done: normalp05/mean/peak + axial.7355/1/1.25/1.5N + thumb gravity/dynamics within URDF effort, max44.24%; thumb4 reaches position bound; actual hardware stiffness/limits/forces unread; nonmoving measurement entry verified",
  "real_robot_ran": false,
  "delivery_complete": false,
  "active_jobs": [],
  "next": "Commit reviewed public files and publish exact source tree",
  "last_event": {
    "utc": "2026-10-05T15:26:24.432173+00:00",
    "event": "publication_staging_ignore_rule_corrected",
    "evidence": "research/singlepush-20261005/events.jsonl",
    "config": {
      "failure": "Global JSON ignore prevented first commit; empty-tree publication attempt rejected422, no branch published",
      "action": "Whitelist public JSON/JSONL only; explicitly ignore private Goal"
    },
    "actor_sha256": "6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e",
    "next": "Commit reviewed public files and publish exact source tree"
  },
  "reproducible_restore_passed": true
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
