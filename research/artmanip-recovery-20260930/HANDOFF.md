# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T08:29:15.797435+00:00",
  "event": "archive_completed",
  "name": "recovery-rl500-development",
  "archive": "delivery/artmanip-recovery-20260930/recovery-rl500-development.tar.gz",
  "sha256": "e035b53287fbd70e86cbfc6b129cf15ab4706b1e9e5c27055214108f5f797663",
  "size": 74197700,
  "files": 24,
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
  "phase": "A complete; B formal segment1; C BC6400 training complete, RL500/BC6400 development live",
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
      "heartbeat": "2026-09-30T08:27:43.480487+00:00",
      "elapsed_seconds": 4368.062454732004,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "source_sha256": "f3aa89d7dd469f42563d350d539692893c96bccfc1edbed3afc06947af96c54e",
      "name": "bc6400-rl500-evaluation-job",
      "gpu": 1,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "bc6400-rl500-evaluation",
        "--states",
        "research/artmanip-recovery-20260930/data/development-all.npy",
        "--models",
        "rl500=runs/recovery-rl-seg1-retry1/checkpoints/epoch_000500.pth",
        "M900=runs/artmanip-recovery-20260930/bc-pair6400/M/epoch_000900.pth",
        "E900=runs/artmanip-recovery-20260930/bc-pair6400/E/epoch_000900.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 3000,
      "started": "2026-09-30T08:20:16.246359+00:00",
      "pid": 12502,
      "status": "running",
      "child_pid": 12503,
      "heartbeat": "2026-09-30T08:27:48.412949+00:00",
      "elapsed_seconds": 452.0687139189977,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/bc6400-rl500-evaluation-job/status.json",
      "pid_exists": true
    }
  ],
  "gpu_hours": 2.9604366438888885,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Finish BC6400/RL500 independent evaluation; likely continue paired12800 since both heldout target errors still decrease. RL firstsegment continues1000 then remaining3segments.",
  "last_event": {
    "utc": "2026-09-30T08:29:15.797435+00:00",
    "event": "archive_completed",
    "name": "recovery-rl500-development",
    "archive": "delivery/artmanip-recovery-20260930/recovery-rl500-development.tar.gz",
    "sha256": "e035b53287fbd70e86cbfc6b129cf15ab4706b1e9e5c27055214108f5f797663",
    "size": 74197700,
    "files": 24,
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
    "bc3200-rl250-evaluation-job",
    "bc-pair6400-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T08:28:10.788409+00:00",
  "next_actions": [
    "Revalidate live jobs: at08:20:12UTC GPU0 RL4900 child4901 sourcepin7cb1b91 and GPU1 evaluation12502 sourcepin6157f9c. No duplicate launches. BC6400 wrapper11727 completed.",
    "BC6400 pair epoch900/Adam7200 passed integrity. Msha8e78b5d41068b3d225caa02c4e1b19ac56e52955af59040e70800d17350e1fed; Esha aaa3cc7e645b160ea10612c8c539be76596212e7738b037e9f05f5b0f58f8927. Validationtarget M .000397536 E .000366444, improvement18/26percent from3200. E700temporarysource3fit spike recovered by800/900, trainprobe also spiked, no persistent overfit.",
    "Current eval bc6400-rl500-evaluation runs rl500 thenM900 thenE900, S2/S5/F each, dev32/source. Pull full npz and independent summarize/gate before next experiment. If no fault, paired12800: namebc-pair12800 previous-namebc-pair6400 previous-epoch900 end-epoch1700, timeout2400/max-seconds1000 perarm enough by observed178sec/400epochs. Predeclare update budget and recordcontinuation; do not stop atshortstrict plateau.",
    "RL500 CP exists local/remote and passed Adam18000/frame40960000/RNG, sha765063c19666ac3c4551437563c981bef1a13934af9dd01eb2d2e9a6bdfa6cb4. RL250 F31/32/31/30 butbody0 andalive6/2/27/0, S0. Continue1000endpoint andactualrestore→2000→3000→4000. Do not replace originalreference byfixedclockfine-tune before baselinebudget. Later holdingcomparison may use a common substantivecheckpoint ifstabilityremainslow.",
    "Launcher now refreshes real jobs and reserves all live remaining timeouts plus proposed timeout. Uses22GPUh pre-final ceiling and21:12UTC training cutoff. Final128 still unopened/untransferred. No student or secondseed until exactS64gate.",
    "GitHub confirmedb3c72ea; BC6400 archive actualextract28files+CPUAdam7200 passed. Uploadsession98413 /tmp/wuji-recovery-incremental-upload8.log maystillactive, checkbeforeanotheruploader. Release399789402 draft, final16assets expected after6400 upload. weights-index currently20/13 mustrefreshlater. Video/finalfreeze/final128/publicrelease stillpending.",
    "CPU scripts: plot_wuji_recovery_learning exports separated training/fit/development trends; diagnose_wuji_recovery_state_shift measures matched-time physical q/target distribution shift. Existing bc800 shift does not triggerDAgger because validation still improves; do not add lossmodules now."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair6400"
}
```
