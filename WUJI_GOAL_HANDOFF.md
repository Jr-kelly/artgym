# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T12:48:25.940971+00:00",
  "event": "bc32000_actual_parent_restore_verified",
  "evidence": "research/artmanip-recovery-20260930/bc32000-actual-resume.json",
  "actual_resume": [
    {
      "arm": "M",
      "parent_sha256": "d1780b90eda8ce7e3d437465a90a0418503ba8de02ef2a8a4b475300c114b6b3",
      "saved_start_sha256": "dd356f46d20eb1157f2f128f7f801f8ab94396f503bd12c5efd03df1586ddfb9",
      "equal_fields": [
        "model",
        "bc_optimizer",
        "bc_torch_rng",
        "bc_cuda_rng",
        "bc_numpy_rng",
        "bc_epoch",
        "bc_updates"
      ],
      "first_epoch": 2501,
      "first_updates": 20008
    },
    {
      "arm": "E",
      "parent_sha256": "0f8256a45fe685674272165ea2a1c213a9f753951c89c9b1a2c61e82726ba41a",
      "saved_start_sha256": "79f9e3e4598b53518b6aefaefa633bc26feb7f309e4dae88f666f57a17d65a3a",
      "equal_fields": [
        "model",
        "bc_optimizer",
        "bc_torch_rng",
        "bc_cuda_rng",
        "bc_numpy_rng",
        "bc_epoch",
        "bc_updates"
      ],
      "first_epoch": 2501,
      "first_updates": 20008
    }
  ],
  "next": "Restore the splitM/E archives together and verify final paired states; complete current independentdevelopment, then matched originalRL control."
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
      "name": "bc32000-development-job",
      "gpu": 1,
      "final_phase": false,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "bc32000-development",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "M4100=runs/artmanip-recovery-20260930/bc-pair32000/M/epoch_004100.pth",
        "E4100=runs/artmanip-recovery-20260930/bc-pair32000/E/epoch_004100.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 1800,
      "started": "2026-09-30T12:42:44.052075+00:00",
      "pid": 42986,
      "status": "running",
      "child_pid": 42987,
      "heartbeat": "2026-09-30T12:44:44.684122+00:00",
      "elapsed_seconds": 120.52476944100636,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc32000-development-job/status.json",
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
      "heartbeat": "2026-09-30T12:44:25.698044+00:00",
      "elapsed_seconds": 2832.135712238989,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg3-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 11.033471045555551,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 original segment3→3000, mandatorydev, segment4→4000. GPU1 bc32000-development wrapper42986 running; after complete immediately start matched repaired-pool original RL1000→2000, while independently rescoring BC.",
  "last_event": {
    "utc": "2026-09-30T12:48:25.940971+00:00",
    "event": "bc32000_actual_parent_restore_verified",
    "evidence": "research/artmanip-recovery-20260930/bc32000-actual-resume.json",
    "actual_resume": [
      {
        "arm": "M",
        "parent_sha256": "d1780b90eda8ce7e3d437465a90a0418503ba8de02ef2a8a4b475300c114b6b3",
        "saved_start_sha256": "dd356f46d20eb1157f2f128f7f801f8ab94396f503bd12c5efd03df1586ddfb9",
        "equal_fields": [
          "model",
          "bc_optimizer",
          "bc_torch_rng",
          "bc_cuda_rng",
          "bc_numpy_rng",
          "bc_epoch",
          "bc_updates"
        ],
        "first_epoch": 2501,
        "first_updates": 20008
      },
      {
        "arm": "E",
        "parent_sha256": "0f8256a45fe685674272165ea2a1c213a9f753951c89c9b1a2c61e82726ba41a",
        "saved_start_sha256": "79f9e3e4598b53518b6aefaefa633bc26feb7f309e4dae88f666f57a17d65a3a",
        "equal_fields": [
          "model",
          "bc_optimizer",
          "bc_torch_rng",
          "bc_cuda_rng",
          "bc_numpy_rng",
          "bc_epoch",
          "bc_updates"
        ],
        "first_epoch": 2501,
        "first_updates": 20008
      }
    ],
    "next": "Restore the splitM/E archives together and verify final paired states; complete current independentdevelopment, then matched originalRL control."
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
    "holding2000-development-job",
    "bc-pair32000-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T12:44:46.224299+00:00",
  "next_actions": [
    "GPU0 segment3 wrapper38444 reverified12:24UTC, epoch2212. ActualCP2000→2001 model and Adam72000→72036 restore passed; continue to3000, mandatorydevelopment, then fourthsegment4000. Runtime randomize=false/joint_noise=0/force_scale=0.",
    "Repaired training pool d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed full51220sec static and clock/mapping checks. Four source0 slots47/94/104/117 replaced by original0/1/2/3, distinctcounts124/128/128/128. No evaluation filtering.",
    "Holding2000 completed and independently rescored: S2strict[11,0,0,0], S5strictall0; Fcycles[32,32,0,32], source3bodyall0. Retain earlier holding1500; no blind extension while source2F regresses. Matched repaired-pool original CP1000→2000 remains required.",
    "PairedBC32000 completed2500→4100. Msha ca65222b793f7a1dd5669652ace4413b213e018ef26b77eb78c80696940ca25a, Esha7d6432a7110019abc112b9cd3321a45c56e72eb1b0c88f2ade5747b638b89410. Adam32800/28frozen/sameRNG passed. GPU1 BC4100dev wrapper42986 running; then repairedoriginalcontrol.",
    "Final128 stillunopened/untransferred. Finalfreeze, once-onlyassessment, videos,publicRelease/downloadrestore/processcleanup remain.",
    "GitHubconfirmed857270b. Draft33assets; BC32000 archive currentlybeingbuilt. Freezehelper implemented butNOTexecuted. Finalreserve4GPUh/2wallh enforced bylauncher20GPUh/20:42cutoff; nofinalscores/video/publicReleaseyet."
  ],
  "training_active_run": "runs/recovery-rl-seg3",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000"
}
```
