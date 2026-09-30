# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T09:08:48.388095+00:00",
  "event": "paired12800_independent_result_recorded",
  "evidence": [
    "research/artmanip-recovery-20260930/bc12800-analysis/report.json",
    "research/artmanip-recovery-20260930/bc12800-gates.json",
    "research/artmanip-recovery-20260930/bc19200-plan.json"
  ],
  "M_source3_S2_S5": [
    12,
    10
  ],
  "E_source3_S2_S5": [
    14,
    11
  ],
  "M_source3_body": [
    29,
    31
  ],
  "E_source3_body": [
    32,
    31
  ],
  "M_phase_hold": [
    0.834375,
    0.78125
  ],
  "E_phase_hold": [
    0.8625,
    0.71875
  ],
  "FbodyM": [
    32,
    27,
    25,
    21
  ],
  "FbodyE": [
    32,
    26,
    28,
    24
  ],
  "n": 32,
  "decision": "Bodyandofflinefitimprovementsjustifyboundedextra6400updateswithinBC2GPUh; keep allfixedendpoints, neitherSgatenor64trigger.",
  "next": "RL firstsegment1000 due soon: verifywrapperfinished/checkpoint thencontinue2000sameAdam/RNG onGPU0. BC19200train1700→2500 onGPU1, thenRL1000+M2500/E2500dev whenfree."
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
  "phase": "A complete; B formal segment1nearing1000; C paired19200extensiontraining",
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
      "heartbeat": "2026-09-30T09:07:53.783606+00:00",
      "elapsed_seconds": 6778.365412676008,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/rl-seg1-retry1-job/status.json",
      "pid_exists": true
    },
    {
      "name": "bc-pair19200-job",
      "gpu": 1,
      "timeout": 2400,
      "command": [
        "PYTHON",
        "-m",
        "scripts.run_wuji_recovery_bc_pair",
        "--name",
        "bc-pair19200",
        "--previous-name",
        "bc-pair12800",
        "--previous-epoch",
        "1700",
        "--end-epoch",
        "2500",
        "--max-seconds",
        "1000"
      ],
      "source_sha": "14c42ed25377e114e755a633c1edd6e60ae5fede",
      "created_utc": "2026-09-30T09:08:09.318787+00:00",
      "budget_receipt_utc": "2026-09-30T09:08:09.070008+00:00",
      "occupied_gpu_hours": 4.202169544166667,
      "other_jobs_reserved_gpu_hours": 0.4461065644444446,
      "root": "/tmp/artgym-recovery-20260930",
      "pin": "/tmp/artgym-recovery-20260930/pins/14c42ed25377e114e755a633c1edd6e60ae5fede",
      "pid": 17663
    }
  ],
  "gpu_hours": 4.202169544166667,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "RL firstsegment1000 due soon: verifywrapperfinished/checkpoint thencontinue2000sameAdam/RNG onGPU0. BC19200train1700→2500 onGPU1, thenRL1000+M2500/E2500dev whenfree.",
  "last_event": {
    "utc": "2026-09-30T09:08:48.388095+00:00",
    "event": "paired12800_independent_result_recorded",
    "evidence": [
      "research/artmanip-recovery-20260930/bc12800-analysis/report.json",
      "research/artmanip-recovery-20260930/bc12800-gates.json",
      "research/artmanip-recovery-20260930/bc19200-plan.json"
    ],
    "M_source3_S2_S5": [
      12,
      10
    ],
    "E_source3_S2_S5": [
      14,
      11
    ],
    "M_source3_body": [
      29,
      31
    ],
    "E_source3_body": [
      32,
      31
    ],
    "M_phase_hold": [
      0.834375,
      0.78125
    ],
    "E_phase_hold": [
      0.8625,
      0.71875
    ],
    "FbodyM": [
      32,
      27,
      25,
      21
    ],
    "FbodyE": [
      32,
      26,
      28,
      24
    ],
    "n": 32,
    "decision": "Bodyandofflinefitimprovementsjustifyboundedextra6400updateswithinBC2GPUh; keep allfixedendpoints, neitherSgatenor64trigger.",
    "next": "RL firstsegment1000 due soon: verifywrapperfinished/checkpoint thencontinue2000sameAdam/RNG onGPU0. BC19200train1700→2500 onGPU1, thenRL1000+M2500/E2500dev whenfree."
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
    "bc12800-evaluation-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T09:08:09.070008+00:00",
  "next_actions": [
    "Revalidatejobs: RL4900 GPU0, newBC19200wrapper fromjobs/bc-pair19200-job.json GPU1; BC12800eval16161completed. RLwas910at09:07UTC andend1000expected~09:18UTC.",
    "BC12800 independentS: Msource3S2/S5=12/10 body29/31; E=14/11 body32/31, a realbodyimprovementvs29/24at6400. E S5phase.719vs.656; allF32cycles. NoSgate/64. Extra6400updates to19200totalpredeclared bc19200-plan.json becausebothheldouttargetsandbodyimprove;12800suggestionnotusedasautomaticstop. BCtrainingbefore=.4084GPUh/2h.",
    "BC19200 plannedepoch2500/Adam20000; pullweights/audit/fitallpairs, thenindependentM2500/E2500S2/S5/F plusRL1000ifready. Keep fixed12800endpoints. Subsequentchoicejointtrends, notstrict-only. NoDAgger/physicaltargetlossyetbecauseofflineeffectivetargeterrorsnotstable; state-shiftevidenceavailable.",
    "RL1000 continuation use train_wuji_recovery_rl task=wuji_artmanip_reference hand=wuji_paper_official_actuator object=knife_wuji_reference train=wujiArtManipReferenceSAPG num_envs=5120 headless=True pipeline=gpu graphics_device_id=-1 force_render=False num_subscenes=0 multi_gpu=False seed=2026093011 experiment=recovery-rl-seg2 max_iterations=2000 checkpoint=runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth save_frequency/evaluation_frequency250 checkpoint_first_epoch1250. Wrappertimeout8400 GPU0. VerifyCP1000epoch/frame81920000/Adam36000 andstartuprestore beforeclaim. Preserveoriginal200→2000curriculum and4endpoints1000/2000/3000/4000.",
    "Launcher now refreshes real jobs and reserves all live remaining timeouts plus proposed timeout. Uses22GPUh pre-final ceiling and21:12UTC training cutoff. Final128 still unopened/untransferred. No student or secondseed until exactS64gate.",
    "GitHubconfirmed14c42ed; subsequentreceiptsuncommitted. Release399789402draft20assetsserververified inclBC12800andRL750, upload12finished. NewBC12800evalarchivependingupload. weightsindexstale20/13refreshlater. Final128stillunopened,videoactualnone,finalpublicrelease/downloadrestore/cleanuprequired.",
    "CPU scripts: plot_wuji_recovery_learning exports separated training/fit/development trends; diagnose_wuji_recovery_state_shift measures matched-time physical q/target distribution shift. Existing bc800 shift does not triggerDAgger because validation still improves; do not add lossmodules now."
  ],
  "training_active_run": "runs/recovery-rl-seg1-retry1",
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair12800"
}
```
