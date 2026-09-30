# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T12:30:17.018625+00:00",
  "event": "final_freeze_tool_added_without_freezing",
  "source": "scripts/freeze_wuji_recovery.py",
  "validation": "Syntax check and rank parity against existing independent development gate ordering passed. No final manifest created, cohort evaluated or final model selected.",
  "next": "Continue active originalRL and pairedBC. Use helper only after mandatory experiments and evidence-based development stop."
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
      "name": "bc-pair32000-job",
      "gpu": 1,
      "final_phase": false,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.run_wuji_recovery_bc_pair",
        "--name",
        "bc-pair32000",
        "--previous-name",
        "bc-pair19200",
        "--previous-epoch",
        "2500",
        "--end-epoch",
        "4100",
        "--max-seconds",
        "1100"
      ],
      "timeout_seconds": 2700,
      "started": "2026-09-30T12:17:29.619596+00:00",
      "pid": 40915,
      "status": "running",
      "child_pid": 40916,
      "heartbeat": "2026-09-30T12:27:02.151385+00:00",
      "elapsed_seconds": 572.478231178,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc-pair32000-job/status.json",
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
      "heartbeat": "2026-09-30T12:27:21.382694+00:00",
      "elapsed_seconds": 1807.8302182859916,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg3-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 10.490737223611108,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 original segment3→3000→4000. GPU1 pairedBC32000 just launched after holding2000 dev completed; then BCdev and repaired-pool original control1000→2000.",
  "last_event": {
    "utc": "2026-09-30T12:30:17.018625+00:00",
    "event": "final_freeze_tool_added_without_freezing",
    "source": "scripts/freeze_wuji_recovery.py",
    "validation": "Syntax check and rank parity against existing independent development gate ordering passed. No final manifest created, cohort evaluated or final model selected.",
    "next": "Continue active originalRL and pairedBC. Use helper only after mandatory experiments and evidence-based development stop."
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T12:17:14Z",
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
    "holding2000-development-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T12:27:28.035207+00:00",
  "next_actions": [
    "GPU0 segment3 wrapper38444 reverified12:24UTC, epoch2212. ActualCP2000→2001 model and Adam72000→72036 restore passed; continue to3000, mandatorydevelopment, then fourthsegment4000. Runtime randomize=false/joint_noise=0/force_scale=0.",
    "Repaired training pool d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed full51220sec static and clock/mapping checks. Four source0 slots47/94/104/117 replaced by original0/1/2/3, distinctcounts124/128/128/128. No evaluation filtering.",
    "Holding2000 completed and independently rescored: S2strict[11,0,0,0], S5strictall0; Fcycles[32,32,0,32], source3bodyall0. Retain earlier holding1500; no blind extension while source2F regresses. Matched repaired-pool original CP1000→2000 remains required.",
    "GPU1 bc-pair32000 wrapper40915 frompin0bccbf3 running2500→4100, identical pairedAdam/RNG, cumulativeadded32000. After completion audit/dev then matched repairedoriginalcontrol. No64promotion/secondseed/student.",
    "Final128 stillunopened/untransferred. Finalfreeze, once-onlyassessment, videos,publicRelease/downloadrestore/processcleanup remain.",
    "GitHubconfirmed13a0b1c. Draft33assets includes holding endpoint and development; finalpublicRelease/downloadrestore/videospending. Latest4h38.35percent/0gaps at12:09UTC. Reserve4GPUh/2h for final; ordinarylauncher usesSTATE reserve."
  ],
  "training_active_run": "runs/recovery-rl-clockhold-clean",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair19200"
}
```
