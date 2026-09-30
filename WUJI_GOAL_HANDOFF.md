# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T13:48:05.315865+00:00",
  "event": "failure_video_selection_rule_prepared",
  "evidence": "research/artmanip-recovery-20260930/failure-video-selection-validation.json",
  "next": "Freeze candidate later; render four fixed rows plus frozen first-failure example if required; retain local-versus-development differences"
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
      "heartbeat": "2026-09-30T13:43:40.549508+00:00",
      "elapsed_seconds": 6386.9730409529875,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg3-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    },
    {
      "source_sha256": "998b1c057e21c029884c58abe3d29ca976f05682d6a54b5092ccd4f3bef4d76e",
      "name": "rl-reference-clean-job",
      "gpu": 1,
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
        "experiment=recovery-rl-reference-clean",
        "max_iterations=2000",
        "checkpoint=runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=1250",
        "task.env.trainingStates=research/artmanip-recovery-20260930/data/rl-train-static-valid.npy"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T12:56:12.129283+00:00",
      "pid": 44425,
      "status": "running",
      "child_pid": 44426,
      "heartbeat": "2026-09-30T13:43:55.093527+00:00",
      "elapsed_seconds": 2862.8669888550066,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-reference-clean-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    }
  ],
  "gpu_hours": 12.981163264722216,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "GPU0 original segment3→3000, development, segment4→4000. GPU1 matched repaired-pool originalcontrol44425 CP1000→2000 just started; after its required dev, execute E-only4100→5700 underbc44800-plan.",
  "last_event": {
    "utc": "2026-09-30T13:48:05.315865+00:00",
    "event": "failure_video_selection_rule_prepared",
    "evidence": "research/artmanip-recovery-20260930/failure-video-selection-validation.json",
    "next": "Freeze candidate later; render four fixed rows plus frozen first-failure example if required; retain local-versus-development differences"
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
    "bc-pair32000-job",
    "bc32000-development-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T13:44:05.025946+00:00",
  "next_actions": [
    "GPU0 originalsegment3 PID38444 at13:03UTC epoch2519. Continue3000; preregistereddev2500+3000 then originalseg4to4000 withdev3500+4000. ActualCP2000→2001restorepassed; originalpoolunchanged.",
    "Repaired training pool d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed full51220sec static and clock/mapping checks. Four source0 slots47/94/104/117 replaced by original0/1/2/3, distinctcounts124/128/128/128. No evaluation filtering.",
    "GPU1 matched repaired-pool originalcontrol PID44425 fromsourcebdd4c7c at13:03UTC epoch1059. ActualCP1000→1001 model/Adamrestore, repairedpoolhash and false/0/0 noise verified. Finish2000, devrlclean1500+2000; compareholdingpoints independently.",
    "BC32000 independentdev passed: E4100 S2[32,32,32,23],S5[31,32,32,14],Fall32; source3phasehold and5sstatecoverage improve. Mclosedloopflat/worse. Preregistered E-only44800additionaltotal end5700, Adam45600; keep paired32000 comparison separate from laterunequal-budget extension.",
    "Final128 stillunopened/untransferred. Finalfreeze, once-onlyassessment, videos,publicRelease/downloadrestore/processcleanup remain.",
    "GitHublastverified and draftassetcount are in dedicatedSTATE fields. Originalcheckpoint weights/rawtraces are incrementally archived/restored/uploaded. Finalfreeze helper exists butNOTexecuted; keep4GPUh/2h reserve. PublicRelease/downloadrestore/videos/cleanup stillrequired."
  ],
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000",
  "training_active_runs": [
    "runs/recovery-rl-seg3",
    "runs/recovery-rl-reference-clean"
  ],
  "bc_next_plan": "research/artmanip-recovery-20260930/bc44800-plan.json",
  "github_last_verified_commit": "48294a6c721c211e2c08cabe08c3f51782f51e8f",
  "release_verified_assets": 37,
  "gpu_hours_by_host": {
    "authorized_remote": 12.981163264722216,
    "local": 0.0
  }
}
```
