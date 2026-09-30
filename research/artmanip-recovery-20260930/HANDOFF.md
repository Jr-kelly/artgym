# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T15:37:03.486226+00:00",
  "event": "e44800_archive_restored_and_development_active",
  "checkpoint_sha256": "2f85fa6b77b9c5358d519dcd816b285efcf33900498400dd54a8ae22bba1fac3",
  "evidence": [
    "research/artmanip-recovery-20260930/bc44800-restored-integrity.json",
    "research/artmanip-recovery-20260930/bc44800-fit-trend.json"
  ],
  "next": "GPU0 originalsegment4 continues to4000, then development3500/4000. GPU1 E5700 development PID57178 started15:34UTC. E44800 training completed, actual parent/Adam/RNG and archive restore passed. After development, independently score and diagnose state shift; choose further learning from phase/body/fit and actual budget."
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
      "name": "bc44800-development-job",
      "gpu": 1,
      "final_phase": false,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "bc44800-development",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "E5700=runs/artmanip-recovery-20260930/bc-executed44800/E/epoch_005700.pth"
      ],
      "timeout_seconds": 1200,
      "started": "2026-09-30T15:34:30.581376+00:00",
      "pid": 57178,
      "status": "running",
      "child_pid": 57179,
      "heartbeat": "2026-09-30T15:36:01.117494+00:00",
      "elapsed_seconds": 90.4225345349987,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc44800-development-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    },
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
      "heartbeat": "2026-09-30T15:36:12.363730+00:00",
      "elapsed_seconds": 4247.6227793,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg4-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    }
  ],
  "gpu_hours": 16.52030672555555,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 originalsegment4 continues to4000, then development3500/4000. GPU1 E5700 development PID57178 started15:34UTC. E44800 training completed, actual parent/Adam/RNG and archive restore passed. After development, independently score and diagnose state shift; choose further learning from phase/body/fit and actual budget.",
  "last_event": {
    "utc": "2026-09-30T15:37:03.486226+00:00",
    "event": "e44800_archive_restored_and_development_active",
    "checkpoint_sha256": "2f85fa6b77b9c5358d519dcd816b285efcf33900498400dd54a8ae22bba1fac3",
    "evidence": [
      "research/artmanip-recovery-20260930/bc44800-restored-integrity.json",
      "research/artmanip-recovery-20260930/bc44800-fit-trend.json"
    ],
    "next": "GPU0 originalsegment4 continues to4000, then development3500/4000. GPU1 E5700 development PID57178 started15:34UTC. E44800 training completed, actual parent/Adam/RNG and archive restore passed. After development, independently score and diagnose state shift; choose further learning from phase/body/fit and actual budget."
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
    "bc-executed44800-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T15:36:16.430686+00:00",
  "next_actions": [
    "GPU0: original segment4 wrapper51150, source e80d5f4, started14:25UTC. At14:31UTC epoch3040. CP3000→3001 actual model/Adam restore and effective configuration passed. Finish4000, then development3500+4000. Decide further learning from joint phase/body/training trends and remaining budget; minimum4000 is not a convergence claim.",
    "Matched repaired-pool original control completed2000 and independently scored; see matched-control-comparison.json. Holding improves old-source body but source3 late phases worsen and source2F collapses; retain early candidates, no blind hold2000 continuation.",
    "Repaired training pool SHA d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed512 static20s trials. Replaced source0 slots47/94/104/117 with originals0/1/2/3. Original reference retains its original pool. No development/final filtering.",
    "GPU0 originalsegment4 continues to4000, then development3500/4000. GPU1 E5700 development PID57178 started15:34UTC. E44800 training completed, actual parent/Adam/RNG and archive restore passed. After development, independently score and diagnose state shift; choose further learning from phase/body/fit and actual budget.",
    "Final128 remains unopened. Freeze only after evidence-based learning stop/budget decision. Keep4GPUh and2h final reserve. Exact final batch guard exists; transfer frozen JSON and final states only after committed freeze. Final videos use fixed four development rows plus a frozen first-failure example if needed. No local GPU has been started.",
    "GitHub verified17b3c3a and draft40 assets. Latest source/restore/evaluation evidence is committed. Weights index needs refresh. Final public Release, anonymous download/restore, videos, complete report and own-process cleanup remain. Monitor1192 identity last verified14:02UTC; recheck at cleanup."
  ],
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000",
  "training_active_runs": [
    "runs/recovery-rl-seg4"
  ],
  "bc_next_plan": "research/artmanip-recovery-20260930/bc44800-plan.json",
  "github_last_verified_commit": "b8596aa7dda301082e07536a050d6661de25e71f",
  "release_verified_assets": 43,
  "gpu_hours_by_host": {
    "authorized_remote": 16.52030672555555,
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
