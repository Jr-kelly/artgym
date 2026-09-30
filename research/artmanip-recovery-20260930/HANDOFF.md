# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T12:13:40.362581+00:00",
  "event": "evaluation_control_metadata_override_removed",
  "file": "scripts/evaluate_wuji_recovery.py",
  "finding": "A legacy final assignment overwrote the newer full_incremental report with all_joint_incremental step_rad only. Removed that assignment so future reports retain effective_target_step_rad and control_dt. Actual control step remains1/120rad peraction; no simulation, trajectory or scoring code changed.",
  "live_pins": "Unchanged: running holding development and original segment3 retain their original immutable source.",
  "next": "Future evaluation records complete effective interface metadata; preserve historical reports as originally generated."
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
      "name": "holding2000-development-job",
      "gpu": 1,
      "final_phase": false,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "holding2000-development",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "rlhold1750=runs/recovery-rl-clockhold-clean/checkpoints/epoch_001750.pth",
        "rlhold2000=runs/recovery-rl-clockhold-clean/checkpoints/epoch_002000.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 1800,
      "started": "2026-09-30T12:03:13.399728+00:00",
      "pid": 39392,
      "status": "running",
      "child_pid": 39393,
      "heartbeat": "2026-09-30T12:10:15.394529+00:00",
      "elapsed_seconds": 421.9191256900085,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/holding2000-development-job/status.json",
      "pid_exists": true
    },
    {
      "source_sha256": "998b1c057e21c029884c58abe3d29ca976f05682d6a54b5092ccd4f3bef4d76e",
      "name": "rl-seg3-job",
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
        "experiment=recovery-rl-seg3",
        "max_iterations=3000",
        "checkpoint=runs/recovery-rl-seg2/checkpoints/epoch_002000.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=2250"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T11:57:13.483470+00:00",
      "pid": 38444,
      "status": "running",
      "child_pid": 38445,
      "heartbeat": "2026-09-30T12:10:17.056580+00:00",
      "elapsed_seconds": 783.4524852069881,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg3-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 9.938214839999997,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 original segment3 CP2000→3000 running, then mandatory dev and segment4→4000. GPU1 holding2000 endpoint, dev, pairedBC32000, matched repaired-pool original objective control1000→2000.",
  "last_event": {
    "utc": "2026-09-30T12:13:40.362581+00:00",
    "event": "evaluation_control_metadata_override_removed",
    "file": "scripts/evaluate_wuji_recovery.py",
    "finding": "A legacy final assignment overwrote the newer full_incremental report with all_joint_incremental step_rad only. Removed that assignment so future reports retain effective_target_step_rad and control_dt. Actual control step remains1/120rad peraction; no simulation, trajectory or scoring code changed.",
    "live_pins": "Unchanged: running holding development and original segment3 retain their original immutable source.",
    "next": "Future evaluation records complete effective interface metadata; preserve historical reports as originally generated."
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T10:52:41Z",
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
    "rl-clockhold-clean-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T12:10:44.291691+00:00",
  "next_actions": [
    "GPU0 segment3 wrapper38444 reverified12:01UTC, actualCP2000→2001 model and Adam72000→72036 restore passed. Runtime randomize=false/joint_noise=0/force_scale=0.",
    "Repaired training pool d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed full51220sec static and clock/mapping checks. Four source0 slots47/94/104/117 replaced by original0/1/2/3, distinctcounts124/128/128/128. No evaluation filtering.",
    "GPU1 rl-clockhold-clean-job25006 is running; sourcepin81a60a8, actualRL1000→1001 optimizer/model restore verified. Uses repaired pool, target2000. Matched repaired-pool original goalCP1000→2000 remainsrequired after BC32000.",
    "BC M/E2500 independentdevelopment recorded: E21/32 S2source3,11/32 S5source3,allSbody32/32; stillimproving. Execute preregistered paired32000addedupdates2500→4100 after holding, then independentdev. No S64 gate/secondseed/student yet.",
    "Final128 stillunopened/untransferred. Finalfreeze, once-onlyassessment, videos,publicRelease/downloadrestore/processcleanup remain.",
    "GitHubconfirmed61f8c7c; localdf67a04 adds effective-control/noise logging only (future runs, livepins unchanged). Draft30assets expected upload22completed; finalpublicRelease/downloadrestore/videos pending. Full4h26percentthresholdpassed36.49, recent30min41.73 at10:52UTC."
  ],
  "training_active_run": "runs/recovery-rl-clockhold-clean",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair19200"
}
```
