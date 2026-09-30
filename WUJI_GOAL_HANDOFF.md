# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T16:08:44.195638+00:00",
  "event": "archive_completed",
  "name": "recovery-aggregation1-collection",
  "archive": "delivery/artmanip-recovery-20260930/recovery-aggregation1-collection.tar.gz",
  "sha256": "dc9b090813098d5b467551e558a17d70754002b4beb45fc480e22f9ba712273b",
  "size": 395266433,
  "files": 103,
  "next": "Restore-check and upload; local originals retained"
}
```

预算与任务状态：
```json
{
  "start_utc": "2026-09-30T06:42:33+00:00",
  "deadline_utc": "2026-09-30T22:42:33+00:00",
  "training_cutoff_utc": "2026-09-30T20:42:33+00:00",
  "max_gpu_hours": 24,
  "reserved_final_gpu_hours": 4,
  "max_concurrent_gpus": 2,
  "rl_default_gpu_hours": 16,
  "bc_default_gpu_hours": 2,
  "phase": "B/C active; actual stages and next decisions in active_jobs and next_actions",
  "active_jobs": [
    {
      "source_sha256": "998b1c057e21c029884c58abe3d29ca976f05682d6a54b5092ccd4f3bef4d76e",
      "name": "rl-seg4-job",
      "gpu": 0,
      "final_phase": false,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.train_wuji_recovery_rl",
        "task=wuji_artmanip_reference",
        "hand=wuji_paper_official_actuator",
        "object=knife_wuji_reference",
        "train=wujiArtManipReferenceSAPG",
        "num_envs=5120",
        "headless=True",
        "pipeline=gpu",
        "graphics_device_id=-1",
        "force_render=False",
        "num_subscenes=0",
        "multi_gpu=False",
        "seed=2026093011",
        "experiment=recovery-rl-seg4",
        "max_iterations=4000",
        "checkpoint=runs/recovery-rl-seg3/checkpoints/epoch_003000.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=3250"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T14:25:24.648020+00:00",
      "pid": 51150,
      "status": "running",
      "child_pid": 51151,
      "heartbeat": "2026-09-30T16:06:20.370677+00:00",
      "elapsed_seconds": 6055.607467775,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg4-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    }
  ],
  "gpu_hours": 17.40526096944444,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 originalsegment4 continues to4000, then development3500/4000. GPU1 E5700 development PID57178 started15:34UTC. E44800 training completed, actual parent/Adam/RNG and archive restore passed. After development, independently score and diagnose state shift; choose further learning from phase/body/fit and actual budget.",
  "last_event": {
    "utc": "2026-09-30T16:08:44.195638+00:00",
    "event": "archive_completed",
    "name": "recovery-aggregation1-collection",
    "archive": "delivery/artmanip-recovery-20260930/recovery-aggregation1-collection.tar.gz",
    "sha256": "dc9b090813098d5b467551e558a17d70754002b4beb45fc480e22f9ba712273b",
    "size": 395266433,
    "files": 103,
    "next": "Restore-check and upload; local originals retained"
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T14:02:23.439782+00:00",
    "command_verified": "python3 -m scripts.monitor_wuji_recovery_resources"
  },
  "recorded_finished_jobs": [
    "g0-regression-job",
    "rl-pilot20-job",
    "rl-pilot20-retry1-job",
    "reference-precheck-job",
    "rl-pilot20-retry2-job",
    "g0-regression-retry1-job",
    "pilot-evaluation-job",
    "bc-pair800-job",
    "rl-seg1-job",
    "bc800-evaluation-job",
    "bc-pair1600-job",
    "bc1600-evaluation-job",
    "bc-pair3200-job",
    "bc3200-rl250-evaluation-job",
    "bc-pair6400-job",
    "bc6400-rl500-evaluation-job",
    "bc-pair12800-job",
    "bc12800-evaluation-job",
    "rl-seg1-retry1-job",
    "bc-pair19200-job",
    "bc19200-rl1000-evaluation-job",
    "holding-precheck-job",
    "holding-precheck-retry1-job",
    "holding-precheck-retry2-job",
    "reference-pool-static-job",
    "holding-pool-static-job",
    "holding-repaired-pool-static-job",
    "rl-seg2-job",
    "reference2000-holdingmid-development-job",
    "rl-clockhold-clean-job",
    "holding2000-development-job",
    "bc-pair32000-job",
    "bc32000-development-job",
    "rl-seg3-job",
    "reference3000-development-job",
    "rl-reference-clean-job",
    "reference-clean2000-development-job",
    "bc-executed44800-job",
    "bc44800-development-job",
    "bc44800-confirmation64-job",
    "aggregation1-collection-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T16:06:23.113543+00:00",
  "next_actions": [
    "Original RL segment4 active, wrapper51150 GPU0 started14:25UTC; finish4000 then independent development3500/4000 and decide further training from phase/body/training trends and remaining normal20GPUh.",
    "Aggregation collection wrapper59421 GPU1 started15:59UTC, immutable95f0620, timeout1800. Behavior and scripted handoverS2 completed with exact same-GPU expert replay0; S5 outstanding. Independently assess full availability gate before fitting.",
    "BC independent64 E4100/E5700 source3 S2=46/46 and S5=28/29 of64.32-sample S5 regression not reproduced; noS gate/student promotion. State-shift hypothesis still testable; conditional plan aggregation1-plan.json.",
    "Final128 untouched and nofreeze. Preserve4GPUh/2h reserve. Mandatory baseline minimum4000 is not convergence.",
    "GitHuba3d713e verified; draft45 assets incl E44800 development archive48e9d31e restored. Final weights index, report, frozen evaluation, same-weight video, public release/download restore and own-process cleanup remain."
  ],
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000",
  "training_active_runs": [
    "runs/recovery-rl-seg4"
  ],
  "bc_next_plan": "research/artmanip-recovery-20260930/bc44800-plan.json",
  "github_last_verified_commit": "a3d713ed9bd17bd5b1c7d281a0a73611dde6f44a",
  "release_verified_assets": 45,
  "gpu_hours_by_host": {
    "authorized_remote": 17.40526096944444,
    "local": 0.0
  },
  "bc_executed_endpoint": {
    "path": "runs/artmanip-recovery-20260930/bc-executed44800/E/epoch_005700.pth",
    "sha256": "2f85fa6b77b9c5358d519dcd816b285efcf33900498400dd54a8ae22bba1fac3",
    "epoch": 5700,
    "updates": 45600,
    "updates_after_BC100": 44800
  }
}
```
