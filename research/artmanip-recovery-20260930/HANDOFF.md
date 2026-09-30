# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T07:20:26.454953+00:00",
  "event": "continuation_state_refreshed",
  "evidence": "research/artmanip-recovery-20260930/STATE.json",
  "next": "Finish bc800closedloop then paired1600,3200,6400; optional RL250development; mainRL1000continues",
  "current_boundaries": "BC100newdevF32/32all butbody32/23/20/25; S source3fails; no student; fresh final unopened"
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
  "phase": "B formal joint RL segment1 active; C paired +800 completed, closed-loop evaluation active",
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
      "heartbeat": "2026-09-30T07:16:55.846289+00:00",
      "elapsed_seconds": 120.4285400430017,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "bc800-evaluation-job",
      "gpu": 1,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "bc800-evaluation",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "M200=runs/artmanip-recovery-20260930/bc-pair800/M/epoch_000200.pth",
        "E200=runs/artmanip-recovery-20260930/bc-pair800/E/epoch_000200.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 2400,
      "started": "2026-09-30T07:16:29.317089+00:00",
      "pid": 5172,
      "status": "running",
      "child_pid": 5173,
      "heartbeat": "2026-09-30T07:16:59.536326+00:00",
      "elapsed_seconds": 30.126436749997083,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc800-evaluation-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 0.7093455622222221,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Restore isolated runtime; audit upstream and Wuji; meaningful prechecks; pin four-segment RL budget from full-update throughput.",
  "last_event": {
    "utc": "2026-09-30T07:20:26.454953+00:00",
    "event": "continuation_state_refreshed",
    "evidence": "research/artmanip-recovery-20260930/STATE.json",
    "next": "Finish bc800closedloop then paired1600,3200,6400; optional RL250development; mainRL1000continues",
    "current_boundaries": "BC100newdevF32/32all butbody32/23/20/25; S source3fails; no student; fresh final unopened"
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
    "rl-seg1-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T07:17:11.968115+00:00",
  "next_actions": [
    "Poll current wrappers; never restart existing live jobs. RL source pin7cb1b91, GPU0 PID4900 at2026-09-30T07:17:11Z; C evaluationGPU1 PID5172 same timestamp; revalidate PIDs.",
    "When bc800-evaluation completes, pull raw traces and independently rescore. Then pair1600: previous-name bc-pair800, previous-epoch200, end-epoch300, new name bc-pair1600; both arms must continue unless numerical/overfit fault.",
    "Pair3200: previous-name bc-pair1600, previous-epoch300, end-epoch500; pair6400: previous-name bc-pair3200, previous-epoch500, end-epoch900. Optional12800 uses900→1700 only with improving evidence.",
    "RL CP250 optional dev after BC1600 assessment when GPU1 available; CP500 next optional. RL primary segments cumulative1000,2000,3000,4000; no strict-zero early stopping.",
    "RL evaluation model names MUST start rl so batch evaluator selects incremental/native-observation task; M/E/bc100 use mixed interface. Keep same immutable source pins per running job.",
    "Final new128/source stays untested and absent from remote until model+protocol freeze. Final F/S separate episodes. Public releaseTAG wuji-artmanip-recovery-20260930-v1, draft id399789402; publication awaits final validation/video/downloads."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair800"
}
```
