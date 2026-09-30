# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T08:41:44.881379+00:00",
  "event": "bc6400_closedloop_shift_review",
  "evidence": [
    "research/artmanip-recovery-20260930/bc6400-state-shift.json"
  ],
  "source3_S5_q_fraction_above_expert_heldout_p95": {
    "expert": 0.05003,
    "M500": 0.40827,
    "M900": 0.41589,
    "E500": 0.27713,
    "E900": 0.44891
  },
  "decision": "E900closedloopphysicalshift grows alongsideS5bodydrop despiteofflinefit improvement. This is descriptive association, notcausality; completecurrent12800continuation and inspecteffectiveerrortrajectory beforeDAgger trigger. RLgeometryrows cannotdiagnoseBCgeneralization.",
  "next": "Complete12800 andclosedloop; ifofflineeffectiveerrorsstabilize withpersistentdeficit, allowboundedhistoryconsistentDAgger basedonthisevidence"
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
  "phase": "A complete; B formal segment1; C paired12800 training",
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
      "heartbeat": "2026-09-30T08:39:46.697588+00:00",
      "elapsed_seconds": 5091.323523252999,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "name": "bc-pair12800-job",
      "gpu": 1,
      "timeout": 2400,
      "command": [
        "PYTHON",
        "-m",
        "scripts.run_wuji_recovery_bc_pair",
        "--name",
        "bc-pair12800",
        "--previous-name",
        "bc-pair6400",
        "--previous-epoch",
        "900",
        "--end-epoch",
        "1700",
        "--max-seconds",
        "1000"
      ],
      "source_sha": "66cd4bd5c51eade227b9c1bd1463193ff7247a20",
      "created_utc": "2026-09-30T08:40:15.837161+00:00",
      "budget_receipt_utc": "2026-09-30T08:40:15.372838+00:00",
      "occupied_gpu_hours": 3.340485544444444,
      "other_jobs_reserved_gpu_hours": 0.9109625716666667,
      "root": "/tmp/artgym-recovery-20260930",
      "pin": "/tmp/artgym-recovery-20260930/pins/66cd4bd5c51eade227b9c1bd1463193ff7247a20",
      "pid": 14889
    }
  ],
  "gpu_hours": 3.340485544444444,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Finish paired12800 and inspect validation+closedloop; continue original RL1000/2000/3000/4000. Finalfreeze stillnotopened.",
  "last_event": {
    "utc": "2026-09-30T08:41:44.881379+00:00",
    "event": "bc6400_closedloop_shift_review",
    "evidence": [
      "research/artmanip-recovery-20260930/bc6400-state-shift.json"
    ],
    "source3_S5_q_fraction_above_expert_heldout_p95": {
      "expert": 0.05003,
      "M500": 0.40827,
      "M900": 0.41589,
      "E500": 0.27713,
      "E900": 0.44891
    },
    "decision": "E900closedloopphysicalshift grows alongsideS5bodydrop despiteofflinefit improvement. This is descriptive association, notcausality; completecurrent12800continuation and inspecteffectiveerrortrajectory beforeDAgger trigger. RLgeometryrows cannotdiagnoseBCgeneralization.",
    "next": "Complete12800 andclosedloop; ifofflineeffectiveerrorsstabilize withpersistentdeficit, allowboundedhistoryconsistentDAgger basedonthisevidence"
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
    "bc6400-rl500-evaluation-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T08:40:15.372838+00:00",
  "next_actions": [
    "Revalidate status. At08:40:15UTC GPU0 RL4900 andGPU1 BC12800wrapper14889 live, sourcepin66cd4bd forBC. PriorBC6400/RL500eval12502 completed.",
    "BC6400 independentlyrescored: M900source3S2/S5=9/20,body28/32; E900=15/10,body29/24. Fbothall32cycles butEsource3Fbody16/32. NoS/64gate. Offline target continuesdeclining18/26percent; pair12800 extensionpredeclared inbc12800-plan.json, run900→1700, actualAdamtarget13600.",
    "AfterBC12800finished, pull weights/audit epoch1700Adam13600/RNG, fitallpairs, independentevalM1700/E1700 dev32 S2/S5/F. It maycoincideRL1000endpoint; evaluateRL1000 whenavailable. Needretainfixedbudgetendpoints notjustbest. Ifclosedloopgap persists andofflineeffectiveerror stabilizes, inspect state-shift and consider≤3DAggerrnds orphysicaltargetloss perGOAL; do notautomatically addboth.",
    "RL500 independentlyverifiedF32/32/32/29,alive10/31/19/8,bodyall0;source2breach8.54secversus1.13at250,source3still.707sec. Sstrictall0 butsource3S5phasehold.21875>.0078at250. Continue4segmentoriginalgoal. At624sourcevisits16674/16670/16630/16569 balanced; actualvelocitypenaltyweight -15.6 (notpositiondrift), curriculumadvances. CP750retain; nextmandatory1000dev thenresume2000/3000/4000.",
    "Launcher now refreshes real jobs and reserves all live remaining timeouts plus proposed timeout. Uses22GPUh pre-final ceiling and21:12UTC training cutoff. Final128 still unopened/untransferred. No student or secondseed until exactS64gate.",
    "GitHub confirmed66cd4bd; morelocalreportchanges mayneedpush. Release399789402draft17assets afterRL500upload9verified. weights-index20/13stale refreshlater. Sourceandvideoscripts committed; videosactualpendingfreeze. DELIVERY_AUDIT.md listsremainingfullscope. Final128unopened; publication/downloadrestore/finalcleanup stillrequired.",
    "CPU scripts: plot_wuji_recovery_learning exports separated training/fit/development trends; diagnose_wuji_recovery_state_shift measures matched-time physical q/target distribution shift. Existing bc800 shift does not triggerDAgger because validation still improves; do not add lossmodules now."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair6400"
}
```
