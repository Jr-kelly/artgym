# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T08:14:10.051816+00:00",
  "event": "archive_completed",
  "name": "recovery-bc3200-rl250-evaluation",
  "archive": "delivery/artmanip-recovery-20260930/recovery-bc3200-rl250-evaluation.tar.gz",
  "sha256": "973c195ebf21f3ef055534ab8c03f0e05be837bf49bfc8e0ace72def966a1867",
  "size": 252424692,
  "files": 73,
  "next": "Restore-check and upload; local originals retained"
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
  "phase": "A complete; B formal segment1; C paired6400 training",
  "active_jobs": [
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "rl-seg1-retry1-job",
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
        "experiment=recovery-rl-seg1-retry1",
        "max_iterations=1000",
        "checkpoint=runs/recovery-rl-pilot20-retry2/checkpoints/epoch_000020.pth",
        "train.params.config.save_frequency=250",
        "train.params.config.evaluation_frequency=250",
        "train.params.config.checkpoint_first_epoch=250"
      ],
      "timeout_seconds": 8400,
      "started": "2026-09-30T07:14:55.302419+00:00",
      "pid": 4900,
      "status": "running",
      "child_pid": 4901,
      "heartbeat": "2026-09-30T08:13:09.726616+00:00",
      "elapsed_seconds": 3494.306586742001,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "name": "bc-pair6400-job",
      "gpu": 1,
      "timeout": 2400,
      "command": [
        "PYTHON",
        "-m",
        "scripts.run_wuji_recovery_bc_pair",
        "--name",
        "bc-pair6400",
        "--previous-name",
        "bc-pair3200",
        "--previous-epoch",
        "500",
        "--end-epoch",
        "900",
        "--max-seconds",
        "1000"
      ],
      "source_sha": "4c066c016fe5ffebd4afa4db7d83b621f4529055",
      "created_utc": "2026-09-30T08:13:24.053534+00:00",
      "budget_receipt_utc": "2026-09-30T08:13:23.162218+00:00",
      "occupied_gpu_hours": 2.481630325555555,
      "other_jobs_reserved_gpu_hours": 1.3586802458333334,
      "root": "/tmp/artgym-recovery-20260930",
      "pin": "/tmp/artgym-recovery-20260930/pins/4c066c016fe5ffebd4afa4db7d83b621f4529055",
      "pid": 11727
    }
  ],
  "gpu_hours": 2.481630325555555,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Complete paired6400 and assess M900/E900 plusRL500; continue original RL segment1 to1000 and then2000/3000/4000.",
  "last_event": {
    "utc": "2026-09-30T08:14:10.051816+00:00",
    "event": "archive_completed",
    "name": "recovery-bc3200-rl250-evaluation",
    "archive": "delivery/artmanip-recovery-20260930/recovery-bc3200-rl250-evaluation.tar.gz",
    "sha256": "973c195ebf21f3ef055534ab8c03f0e05be837bf49bfc8e0ace72def966a1867",
    "size": 252424692,
    "files": 73,
    "next": "Restore-check and upload; local originals retained"
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T06:51:00Z"
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
    "bc3200-rl250-evaluation-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T08:13:23.162218+00:00",
  "next_actions": [
    "Revalidate status: at08:13:24UTC GPU0 RL wrapper4900 and GPU1 BC6400 wrapper11727 are live. Prior evaluation9284 completed.",
    "BC3200 independently rescored: M500 source3 S2/S5=12/11, E500=17/19 of32; allF=32. E now stronger worst-strict but notSgate, both still improve heldouttargets. CP6400 training500→900 inprogress.",
    "AfterBC6400 finishes pullweights, audit epoch900/Adam7200/RNG/normalizer, summarize fit from allpairs. Evaluate M900/E900 andRL500 S2/S5/F ondev32; optionalBC12800 ifimproving,900→1700. BC physicalstate diagnostic only ifofflineplateau andclosedloopgap persist.",
    "RL250 independentF=[31,32,31,30]/32, alive=[6,2,27,0],bodyall0; Sstrictall0. Thus completecycles explored, no singlesourcecontrol justified. Preserve4segmentoriginalobjective; holding/fixedclock comparison can follow substantive1000/2000 evidence, not replacebaseline. CP500 soon; ensurepull/Adam18000 audit.",
    "Launcher now refreshes real jobs and reserves all live remaining timeouts plus proposed timeout. Uses22GPUh pre-final ceiling and21:12UTC training cutoff. Final128 still unopened/untransferred. No student or secondseed until exactS64gate.",
    "GitHub latestconfirmed1007ac0 plus4c066c0 local weightsindex needsnextpush. Release399789402 draft13assetsverified. scripts/package_wuji_recovery_video.py supportsS/F independenttrace rescore andfixedrows0,32,64,96; actualvideos awaitfreeze. Final128 remainsunopened.",
    "CPU scripts: plot_wuji_recovery_learning exports separated training/fit/development trends; diagnose_wuji_recovery_state_shift measures matched-time physical q/target distribution shift. Existing bc800 shift does not triggerDAgger because validation still improves; do not add lossmodules now."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair3200"
}
```
