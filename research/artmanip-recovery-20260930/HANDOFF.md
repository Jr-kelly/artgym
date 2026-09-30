# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T09:52:15.215435+00:00",
  "event": "holding_precheck_physical_failure",
  "evidence": [
    "runs/artmanip-recovery-20260930/holding-precheck-retry2/physical-diagnostics.json",
    "runs/artmanip-recovery-20260930/holding-precheck-retry2/failure.json"
  ],
  "finding": "Actual pre-reset source0 trial72 breaches at step2 and terminates step5. This is a physical reset finding, not another infrastructure retry. make_env does not set global RNG; previous128 samples differed despite cfg.seed. Training entry does seed RNG. No formal holding training authorized by precheck yet.",
  "next": "Enumerate all512 frozen training states with explicit global seed and exact per-env row on both task configurations; retain original pool and existing RL, investigate reset matching before any filtering or task change.",
  "budget": "Two bounded600step static diagnostic jobs, at most900seconds each onGPU1; useful physical audit, not filler"
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
  "phase": "A complete; B pilot / C checks",
  "active_jobs": [
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
      "heartbeat": "2026-09-30T09:50:39.407048+00:00",
      "elapsed_seconds": 1837.0286077649944,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg2-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 5.476691574722224,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Complete holding precheck before formal RL1000→2000 controlled comparison. Continue original four-segment RL. BC E still improves; revisit continuation after GPU1 availability.",
  "last_event": {
    "utc": "2026-09-30T09:52:15.215435+00:00",
    "event": "holding_precheck_physical_failure",
    "evidence": [
      "runs/artmanip-recovery-20260930/holding-precheck-retry2/physical-diagnostics.json",
      "runs/artmanip-recovery-20260930/holding-precheck-retry2/failure.json"
    ],
    "finding": "Actual pre-reset source0 trial72 breaches at step2 and terminates step5. This is a physical reset finding, not another infrastructure retry. make_env does not set global RNG; previous128 samples differed despite cfg.seed. Training entry does seed RNG. No formal holding training authorized by precheck yet.",
    "next": "Enumerate all512 frozen training states with explicit global seed and exact per-env row on both task configurations; retain original pool and existing RL, investigate reset matching before any filtering or task change.",
    "budget": "Two bounded600step static diagnostic jobs, at most900seconds each onGPU1; useful physical audit, not filler"
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
    "holding-precheck-retry2-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T09:50:57.906736+00:00",
  "next_actions": [
    "Revalidate jobs in resources/latest.json; timestamps are historical receipts, not current facts.",
    "Holding-precheck retry1 uses public env.reset after harness at_reset_ids failure. Do not launch holding training without passing simulation report.",
    "BC19200 results: E source3 S2=21/32,S5=11/32,Sbody32/32both; M=8/9 and body30/32. No S64 promotion. E continues improving, not overall plateau.",
    "Original RL segment2 target2000 fromCP1000 actual optimizer/RNG restore verified; mandatory original endpoints3000/4000 remain.",
    "After holding comparison re-evaluate continuing BC; source3 S5 distribution shift remains, E S2 shift decreased. New module requires evidence and recorded budget.",
    "New final128 untransferred/unopened. Freeze selected and fixed budget endpoints plus protocols before final evaluation once.",
    "GitHub code/result branch pushed b7ad15b. Draft Release upload17 in progress; check process before additional uploader. Actual final videos/public download/restore/cleanup remain."
  ],
  "training_active_run": "runs/recovery-rl-seg2",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair19200"
}
```
