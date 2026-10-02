# 当前 Wuji 实物尺寸 student 适配 Goal

工作区 `/data/research/artgym-experiments-20260921/real-size-student-adaptation-20261002`。先读 research/real-size-student-adaptation-20261002/{GOAL.md,STATE.json,HANDOFF.md,DECISIONS.jsonl}。禁止子代理；旧最终集关闭。PID/利用率均须重新核实。

```json
{
  "start_utc": "2026-10-02T15:32:09.112725+00:00",
  "historical_gpu_hours": 55.37347835334391,
  "max_gpu_hours": 64,
  "round_max_gpu_hours": 3.5,
  "reserved_final_gpu_hours": 6,
  "max_concurrent_gpus": 4,
  "models": {
    "runs/width-student-distillation-20261002/C1-window1-h200-17314/step_054400.pth": "b537578fc1123a6c3bad0358d8aa122b0c9c97bd970f98984960f685fa787a2f",
    "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8"
  },
  "optimizer_updates": 1600,
  "remote_inventory_verified": true,
  "remote_additional_consumption_unknown": false,
  "goal_complete": true,
  "last_event": {
    "utc": "2026-10-02T16:23:26.062340+00:00",
    "event": "real_size_student_goal_complete_and_published",
    "release_url": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-real-size-student-adaptation-20261002-v1",
    "scientific_commit": "420d84d8e461fb23807c315b7d7ceb823b835bfb",
    "phase": "Complete: paired training, independent confirmation, video and public delivery",
    "state_updates": {
      "goal_complete": true,
      "delivery_complete": true,
      "release_url": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-real-size-student-adaptation-20261002-v1",
      "scientific_commit": "420d84d8e461fb23807c315b7d7ceb823b835bfb",
      "training_closed": true,
      "confirmation_closed": true,
      "gpu_work_closed": true,
      "optimizer_updates": 1600,
      "formal_transitions": 1638400
    },
    "next": "No automatic experiments pending. Preserve R800 and closed confirmation. Next separately registered priority: axial drive and endpoint holding while retaining support stability. Remaining7.882011920672166 GPUh."
  },
  "phase": "Complete: paired training, independent confirmation, video and public delivery",
  "next": "No automatic experiments pending. Preserve R800 and closed confirmation. Next separately registered priority: axial drive and endpoint holding while retaining support stability. Remaining7.882011920672166 GPUh.",
  "active_jobs": [],
  "new_gpu_hours": 0.7445097259839208,
  "cumulative_gpu_hours": 56.11798807932783,
  "remaining_gpu_hours": 7.88201192067217,
  "active_gpu_elapsed_hours": 0,
  "remaining_including_active": 7.88201192067217,
  "asset_frozen": true,
  "training_started": true,
  "formal_transitions": 1638400,
  "candidate_frozen": true,
  "selected_main": "R800",
  "training_closed": true,
  "confirmation_opened": true,
  "confirmation_complete": true,
  "confirmation_closed": true,
  "gpu_work_closed": true,
  "delivery_complete": true,
  "release_url": "https://github.com/Jr-kelly/artgym/releases/tag/wuji-real-size-student-adaptation-20261002-v1",
  "scientific_commit": "420d84d8e461fb23807c315b7d7ceb823b835bfb"
}
```
