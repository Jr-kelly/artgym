# 当前 Wuji 跨宽度 student 蒸馏 Goal

工作区 `/data/research/artgym-experiments-20260921/width-student-distillation-20261002`。先读 research/width-student-distillation-20261002/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。禁止子代理；旧最终集关闭。PID/利用率均须重新核实。

```json
{
  "start_utc": "2026-10-02T06:19:52.569245+00:00",
  "base_sha": "89689142c9f0e52fb679ce710f9c95a55b8a6643",
  "phase": "Prepared branch and evidence public; H200 execution blocked by SSH transport",
  "historical_gpu_hours": 40.43593221975697,
  "max_gpu_hours": 64,
  "reserved_final_gpu_hours": 6,
  "max_concurrent_gpus": 8,
  "new_gpu_hours": 0.039454927178028606,
  "cumulative_gpu_hours": 40.475387146935,
  "remaining_gpu_hours": 23.524612853065,
  "models": {
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "runs/unified-student-20261001/SA-real-51200/step_051200.pth": "16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9"
  },
  "goal_sha256": "ef3c1343a0009c9edabd506ff20d47c1c546ca6320db53d8864e4ed3eec02b78",
  "active_jobs": [],
  "remote_inventory_verified": false,
  "remote_additional_consumption_unknown": true,
  "training_started": false,
  "optimizer_updates": 0,
  "final_opened": false,
  "closed_historical_final_sets": true,
  "next": "Restore provided endpoint connectivity; inventory/reconcile actual remote jobs/devices/cost, then same-H200 precheck/disposable matched updates and formal3200-update C/G window. Goal unfinished; do not rerun completed preparation or historical finals",
  "last_event": {
    "utc": "2026-10-02T07:07:59.259334+00:00",
    "event": "preparation_release_published_and_server_digests_verified",
    "evidence": "research/width-student-distillation-20261002/preparation-release-index.json",
    "state_updates": {
      "delivery": {
        "release_id": 401601529,
        "tag": "wuji-width-student-distillation-20261002-preparation-v1",
        "draft": false,
        "published": true,
        "release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-preparation-v1",
        "assets": 2,
        "digests_verified": true,
        "prepared_packet_restored_files": 161,
        "scientific_training_complete": false
      },
      "blocked_goal_turns": 1
    },
    "phase": "Prepared branch and evidence public; H200 execution blocked by SSH transport",
    "next": "Restore provided endpoint connectivity; inventory/reconcile actual remote jobs/devices/cost, then same-H200 precheck/disposable matched updates and formal3200-update C/G window. Goal unfinished; do not rerun completed preparation or historical finals"
  },
  "active_gpu_elapsed_hours": 0,
  "remaining_including_active": 23.524612853065,
  "fresh_data_generated": true,
  "static_validation_complete": false,
  "training_pools_ready": true,
  "local_multiasset_reset_step_verified": true,
  "h200_precheck_complete": false,
  "local_preparation_complete": true,
  "heldout_static_checks_complete": true,
  "delivery": {
    "release_id": 401601529,
    "tag": "wuji-width-student-distillation-20261002-preparation-v1",
    "draft": false,
    "published": true,
    "release": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-preparation-v1",
    "assets": 2,
    "digests_verified": true,
    "prepared_packet_restored_files": 161,
    "scientific_training_complete": false
  },
  "blocked_goal_turns": 1
}
```
