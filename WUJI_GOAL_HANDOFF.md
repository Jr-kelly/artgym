# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T10:09:52.891107+00:00",
  "event": "development_figures_exported",
  "evidence": "research/artmanip-recovery-20260930/comparison-figures/inputs.json",
  "scope": "Independent development cells, separate BC/RL plots of strict or functional success, phase hold/cycle count, full body stability. No final result. BC PNG visually checked.",
  "next": "Both RL jobs continue to planned endpoints; preserve original goal learning and matched holding comparison."
}
```

预算与任务状态：
```json
{
  "start_utc": "2026-09-30T06:42:33+00:00",
  "deadline_utc": "2026-09-30T22:42:33+00:00",
  "training_cutoff_utc": "2026-09-30T21:12:33+00:00",
  "max_gpu_hours": 24,
  "reserved_final_gpu_hours": 2,
  "max_concurrent_gpus": 2,
  "rl_default_gpu_hours": 16,
  "bc_default_gpu_hours": 2,
  "phase": "B/C active; actual stages and next decisions in active_jobs and next_actions",
  "active_jobs": [
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "rl-clockhold-clean-job",
      "gpu": 1,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.train_wuji_recovery_rl",
        "task=wuji_artmanip_clock_hold",
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
        "experiment=recovery-rl-clockhold-clean",
        "max_iterations=2000",
        "checkpoint=runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=1250",
        "task.env.trainingStates=research/artmanip-recovery-20260930/data/rl-train-static-valid.npy"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T10:05:22.332052+00:00",
      "pid": 25006,
      "status": "running",
      "child_pid": 25007,
      "heartbeat": "2026-09-30T10:07:22.917074+00:00",
      "elapsed_seconds": 120.47355902499112,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-clockhold-clean-job/status.json",
      "pid_exists": true
    },
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "rl-seg2-job",
      "gpu": 0,
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
        "experiment=recovery-rl-seg2",
        "max_iterations=2000",
        "checkpoint=runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=1250"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T09:20:02.262280+00:00",
      "pid": 18856,
      "status": "running",
      "child_pid": 18857,
      "heartbeat": "2026-09-30T10:07:13.684230+00:00",
      "elapsed_seconds": 2831.344598565993,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg2-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 5.931311113333335,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Launch repaired-pool holding RL1000→2000; verify actual startup model/Adam/RNG counters. Original RL segment2 continues through2000, then3000/4000. After holding dev, BC pair32000 and matched repaired-pool original-control1000→2000 remain authorized and required.",
  "last_event": {
    "utc": "2026-09-30T10:09:52.891107+00:00",
    "event": "development_figures_exported",
    "evidence": "research/artmanip-recovery-20260930/comparison-figures/inputs.json",
    "scope": "Independent development cells, separate BC/RL plots of strict or functional success, phase hold/cycle count, full body stability. No final result. BC PNG visually checked.",
    "next": "Both RL jobs continue to planned endpoints; preserve original goal learning and matched holding comparison."
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T08:34:07Z",
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
    "holding-repaired-pool-static-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T10:07:41.298834+00:00",
  "next_actions": [
    "Revalidate GPU0 original rl-seg2-job before decisions; original frozen pool has4/512 static-invalid perturbations, baseline retained and labelled.",
    "Repaired training pool d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836 passed full51220sec static and clock/mapping checks. Four source0 slots47/94/104/117 replaced by original0/1/2/3, distinctcounts124/128/128/128. No evaluation filtering.",
    "Launch GPU1 recovery-rl-clockhold-clean fromCP1000→2000, using repairedpool override. Counterpart recovery-rl-reference-clean must later run sameCP1000→2000 samepool/equalupdates. Original4000baseline remains separate.",
    "BC M/E2500 independentdevelopment recorded: E21/32 S2source3,11/32 S5source3,allSbody32/32; stillimproving. Execute preregistered paired32000addedupdates2500→4100 after holding, then independentdev. No S64 gate/secondseed/student yet.",
    "Final128 stillunopened/untransferred. Finalfreeze, once-onlyassessment, videos,publicRelease/downloadrestore/processcleanup remain.",
    "GitHubconfirmedfe48912; newer49cd4bc local. Draft26assets SHAverified afterupload18; check anyuploader beforelaunchinganother. Detailedplans reset-repair-comparison-plan.json andbc32000-plan.json."
  ],
  "training_active_run": "runs/recovery-rl-seg2",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair19200"
}
```
