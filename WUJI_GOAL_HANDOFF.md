# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T07:37:32.751578+00:00",
  "event": "launcher_outstanding_budget_reservation",
  "evidence": [
    "scripts/launch_wuji_recovery.py"
  ],
  "change": "Before any new launch refresh remote status, then reserve both existing live wrapper remaining timeout and proposed timeout against22GPUh learning ceiling. Source pins already running remain unchanged.",
  "next": "Commit diagnostics and budget check; continue paired3200 after current assessment"
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
  "phase": "A complete; B formal segment1; C paired1600 closed-loop evaluation",
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
      "heartbeat": "2026-09-30T07:36:00.800000+00:00",
      "elapsed_seconds": 1265.4209076190018,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "bc1600-evaluation-job",
      "gpu": 1,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "bc1600-evaluation",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "M300=runs/artmanip-recovery-20260930/bc-pair1600/M/epoch_000300.pth",
        "E300=runs/artmanip-recovery-20260930/bc-pair1600/E/epoch_000300.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 2400,
      "started": "2026-09-30T07:33:05.515604+00:00",
      "pid": 6696,
      "status": "running",
      "child_pid": 6697,
      "heartbeat": "2026-09-30T07:36:06.133699+00:00",
      "elapsed_seconds": 180.56648123899504,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc1600-evaluation-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 1.3020391111111114,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Review paired1600 closed-loop and continue paired3200; RL segment1 cumulative1000 continues with optional250 development",
  "last_event": {
    "utc": "2026-09-30T07:37:32.751578+00:00",
    "event": "launcher_outstanding_budget_reservation",
    "evidence": [
      "scripts/launch_wuji_recovery.py"
    ],
    "change": "Before any new launch refresh remote status, then reserve both existing live wrapper remaining timeout and proposed timeout against22GPUh learning ceiling. Source pins already running remain unchanged.",
    "next": "Commit diagnostics and budget check; continue paired3200 after current assessment"
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
    "bc-pair1600-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T07:36:24.227287+00:00",
  "next_actions": [
    "Recheck live wrappers. At07:34:34UTC GPU0 RL wrapper4900 and GPU1 BC1600 evaluation6696 were live. Do not duplicate jobs.",
    "BC1600 pair has passed actual Adam2400/RNG and frozen-normalizer audit; held-out target errors continue decreasing. Review its S2/S5/F then train pair3200.",
    "Pair3200: previous-name bc-pair1600, previous-epoch300, end-epoch500; pair6400: previous-name bc-pair3200, previous-epoch500, end-epoch900. Optional12800 uses900→1700 only with improving evidence.",
    "RL CP250 optional dev after BC1600 assessment when GPU1 available; CP500 next optional. RL primary segments cumulative1000,2000,3000,4000; no strict-zero early stopping.",
    "RL evaluation model names MUST start rl so batch evaluator selects incremental/native-observation task; M/E/bc100 use mixed interface. Keep same immutable source pins per running job.",
    "Final new128/source stays untested and absent from remote until model+protocol freeze. Final F/S separate episodes. Public releaseTAG wuji-artmanip-recovery-20260930-v1, draft id399789402; publication awaits final validation/video/downloads."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair1600"
}
```
