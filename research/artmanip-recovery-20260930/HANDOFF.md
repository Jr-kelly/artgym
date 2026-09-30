# 当前 ArtManip recovery Goal

工作区 /data/research/artgym-experiments-20260921/artmanip-recovery-20260930

先读 research/artmanip-recovery-20260930/{GOAL.md,STATE.json,DECISIONS.jsonl}。禁止子代理；旧停止规则已替换；旧PID须重查。

最近事件：
```json
{
  "utc": "2026-09-30T18:22:37.743801+00:00",
  "event": "all_development_artifacts_verified_while_final_runs",
  "assets": 59,
  "evidence": [
    "research/artmanip-recovery-20260930/draft-assets-verified.json",
    "research/artmanip-recovery-20260930/seed2-promotion64-archive-restore.json"
  ],
  "next": "Only final-g0/g1 GPU jobs remain. Finish frozen validation, independentlyaudit, renderfixedvideos, publishandverifydownloads, cleanupownprocesses."
}
```

预算与任务状态：
```json
{
  "start_utc": "2026-09-30T06:42:33+00:00",
  "deadline_utc": "2026-09-30T22:42:33+00:00",
  "training_cutoff_utc": "2026-09-30T20:42:33+00:00",
  "max_gpu_hours": 24,
  "reserved_final_gpu_hours": 3.5,
  "max_concurrent_gpus": 2,
  "rl_default_gpu_hours": 16,
  "bc_default_gpu_hours": 2.25,
  "phase": "Final frozen evaluation active; no further training or reselection",
  "active_jobs": [
    {
      "source_sha256": "998b1c057e21c029884c58abe3d29ca976f05682d6a54b5092ccd4f3bef4d76e",
      "name": "final-g1-job",
      "gpu": 1,
      "final_phase": true,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "final-g1",
        "--states",
        "research/artmanip-recovery-20260930/data/final-all.npy",
        "--models",
        "E5700=runs/artmanip-recovery-20260930/bc-executed44800/E/epoch_005700.pth",
        "rl4000=runs/recovery-rl-seg4/checkpoints/epoch_004000.pth",
        "rlhold2000=runs/recovery-rl-clockhold-clean/checkpoints/epoch_002000.pth",
        "Eagg6500=runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006500.pth",
        "bc100=runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth",
        "rl1000=runs/recovery-rl-seg1-retry1/checkpoints/epoch_001000.pth",
        "seed2Eagg6100=runs/artmanip-recovery-20260930/bc-seed2-aggregate3200/E/epoch_006100.pth",
        "historical=runs/unified-policy-20260930/experts/historical.pth",
        "source3=runs/unified-policy-20260930/experts/source3.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 5400,
      "started": "2026-09-30T18:19:42.305122+00:00",
      "pid": 73922,
      "status": "running",
      "child_pid": 73923,
      "heartbeat": "2026-09-30T18:20:12.533146+00:00",
      "elapsed_seconds": 30.109037585003534,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/final-g1-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    },
    {
      "source_sha256": "998b1c057e21c029884c58abe3d29ca976f05682d6a54b5092ccd4f3bef4d76e",
      "name": "final-g0-job",
      "gpu": 0,
      "final_phase": true,
      "command": [
        "/tmp/wuji-recovery-runtime/bin/python",
        "-m",
        "scripts.evaluate_wuji_recovery_batch",
        "--name",
        "final-g0",
        "--states",
        "research/artmanip-recovery-20260930/data/final-all.npy",
        "--models",
        "Eagg6100=runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
        "Ereplay6500=runs/artmanip-recovery-20260930/aggregation1-pair6400/replay/E/epoch_006500.pth",
        "E500=runs/artmanip-recovery-20260930/bc-pair3200/E/epoch_000500.pth",
        "M300=runs/artmanip-recovery-20260930/bc-pair1600/M/epoch_000300.pth",
        "rl3000=runs/recovery-rl-seg3/checkpoints/epoch_003000.pth",
        "rlhold1500=runs/recovery-rl-clockhold-clean/checkpoints/epoch_001500.pth",
        "rlclean2000=runs/recovery-rl-reference-clean/checkpoints/epoch_002000.pth",
        "M4100=runs/artmanip-recovery-20260930/bc-pair32000/M/epoch_004100.pth",
        "E4100=runs/artmanip-recovery-20260930/bc-pair32000/E/epoch_004100.pth",
        "--protocols",
        "S2",
        "S5",
        "F"
      ],
      "timeout_seconds": 5400,
      "started": "2026-09-30T18:19:38.300252+00:00",
      "pid": 73774,
      "status": "running",
      "child_pid": 73775,
      "heartbeat": "2026-09-30T18:20:08.497755+00:00",
      "elapsed_seconds": 30.123537938998197,
      "path": "/tmp/artgym-recovery-20260930/runs/artmanip-recovery-20260930/final-g0-job/status.json",
      "pid_exists": true,
      "host": "authorized_remote"
    }
  ],
  "gpu_hours": 19.983175829722207,
  "base_sha": "c1c489f7f76ba068dc1e583da0b4d14b28b1f443",
  "upstream_sha": "63b94fb3364596db51b7e4651b3c3c98ff994710",
  "authorized_host": "wangjiarui@10.13.160.5:33024",
  "resource_check_utc": "2026-09-30T06:42:41Z",
  "resource_observation": "4 H200 idle, no compute processes; previous /tmp runtime and project absent",
  "next": "Wait existing final-g0/g1 jobs, no duplicate final attempts. Complete raw pull and independent final rescore/audit/gates, fixed videos, publicRelease/downloadrestore and cleanup.",
  "last_event": {
    "utc": "2026-09-30T18:22:37.743801+00:00",
    "event": "all_development_artifacts_verified_while_final_runs",
    "assets": 59,
    "evidence": [
      "research/artmanip-recovery-20260930/draft-assets-verified.json",
      "research/artmanip-recovery-20260930/seed2-promotion64-archive-restore.json"
    ],
    "next": "Only final-g0/g1 GPU jobs remain. Finish frozen validation, independentlyaudit, renderfixedvideos, publishandverifydownloads, cleanupownprocesses."
  },
  "monitor": {
    "pid": 1192,
    "host": "10.13.160.5:33024",
    "checked_utc": "2026-09-30T17:30:19+00:00",
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
    "bc32000-development-job",
    "rl-seg3-job",
    "reference3000-development-job",
    "rl-reference-clean-job",
    "reference-clean2000-development-job",
    "bc-executed44800-job",
    "bc44800-development-job",
    "bc44800-confirmation64-job",
    "aggregation1-collection-job",
    "aggregation1-pair6400-job",
    "rl-seg4-job",
    "aggregation1-development-job",
    "reference4000-development-job",
    "aggregation1-promotion64-job",
    "bc-seed2-executed44800-job",
    "aggregation2-collection-job",
    "bc-seed2-aggregate3200-job",
    "seed2-promotion64-job"
  ],
  "unmetered_cuda_preflight_reserve_gpu_hours": 0.05,
  "last_resource_check_utc": "2026-09-30T18:20:37.244979+00:00",
  "next_actions": [
    "FINAL SET NOW OPEN. No further training, checkpoint reselection or final retry without infrastructure audit. final-freeze.json is immutable, SHA881e2989c91105e4f6fd8b6b0bfa13360cab3e9cccdad5d11e0f190375d73385, committed5dbac12. Frozen simulator source a36219f268ea7776aa58b034f7c82c219f3ba93e. Final state SHA9705b08c2d7fd0db167cb5e0d6c1a0e3e77d4cd0f747d8bd209079cd06ad21d7.",
    "Active remote final GPU0 wrapper73774 and GPU1 wrapper73922 started18:19:35/39UTC, timeout5400each. Reverified18:20:37UTC;19.98318GPUh, both9-model plan files have exact freezehash. Expected54 physical model/protocol cells,216 sourcecells,27648 episodes. No local GPU job yet.",
    "GPU0 final-g0 order: Eagg6100,Ereplay6500,E500,M300,rl3000,rlhold1500,rlclean2000,M4100,E4100. GPU1 final-g1 order: E5700,rl4000,rlhold2000,Eagg6500,bc100,rl1000,seed2Eagg6100,historical,source3. EachS2/S5/F. Freeze contains all exactpaths/hashes; E4100 added before freeze to retain matchedM/E32000 endpoints, E5700 extra44800 separate.",
    "Normal work concluded19.95154GPUh. Totalmax24 plusconservative .05 included at launch; final9/9 timeout5400each and3localvideos500each worsttotal~23.4182. Deadline22:42:33UTC; no need use remainingbudget fortraining. OriginalRL4000 remains budget-limited, notconverged.",
    "Second full optimization seed completed E44800+owncollection+aggregate3200. Endpoint seed2Eagg6100 SHA054a32298af88e287cbaa6ef057389489996f3cc102546db86632dad4c3e64e9, Adam48800/28frozen/actualparent/RNG/archiverestorepassed. SharedBC100/experts, notindependentpretraining.",
    "Seed2 exact64 S gate FAILED ONLY source1S2 relativebody:62/64 vs expert64/64, drop3.125pp >3pp by.125pp. S2strict[64,62,63,58],S5[63,64,63,60]. BodyS2[64,62,63,64],S5[63,64,63,64]. All absoluteS gatespass; do notlabel fullS64pass. Fcyclesall64,body[63,53,51,64]. SECOND_SEED.md/REPLICATION64.md and second-seed-decision.json; primary unchanged.",
    "PrimaryEagg6100 SHA2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8 passedexact64;S2[64,64,63,60],S5[63,64,63,64];bodyS2[64,64,63,64],S5[63,64,63,64]. Finalresultpending; no student/hardwareclaim.",
    "After finaljobs finish: status --pull omitsNPZ/PTH/MP4, so full rsync final-g0/final-g1. RuntimePython CPU summarize_wuji_recovery --directories both --output research/.../final-analysis; gate_wuji_recovery --reports final-analysis/report.json --experts same final-analysis/report.json; audit_wuji_recovery_final --analysis final-analysis --output final-integrity.json enforcesall54/216/27648 unique andexactprovenance. write_wuji_recovery_tables --phase final requires artgym Python (systemPython lacksNumPy).",
    "Archive complete final per-model3protocol directories (avoid>2GiB singleasset); retain batchplans/results andjobmetadata separately. Restore each archive; upload_wuji_recovery only works whileRelease draft. Do notmutate archivedevidence. Update README finaltable andFINAL.md, retainfullDEVELOPMENT/SECOND_SEED/STRICT64.",
    "Videos ONLY after remote jobs done: launch_wuji_recovery_local_video --python /home/agiuser/miniconda3/envs/artgym/bin/python --timeout500, protocolsS2 fixed, S5 fixed, S5 --example failure. Fixedrows[0,32,64,96],failure[0,32,64,97] frompre-finaldev. Same primaryweights; localresimulation maydiffer, independentlyscore anddo notpresume failure reproduced.",
    "LocalToDesk2034815 verified17:39UTC desktopC+G video session651MiB;22589MiBfree. Launcher allows only exact /opt/todesk/bin/ToDesk_Session + --isVideoSession=true and>=16000MiBfree; unknowncompute blocks. Realpreflight andnegativeCPUcasespassed. Preserve desktop; cleanup claims onlynoownedcompute, notwholeGPUidle.",
    "package_wuji_recovery_video makes4parallelpanels andscoresframecount/trace. DirectMP4receipt kind standalone_video foruploader/index; rawvideo/report/trace/metadata in separatearchive. If frozenfailure resimpasses, reportthat honestly and retain originaldevelopmentfailure evidence; donotchange finalcohort orweights.",
    "Finalpublicationpending: README coherentnow butdevelopmentstatus, updateafterfinal. weights-index stale195/50: regenerateonceafterallarchives/videos usingCPU index_wuji_recovery_weights; verifyalllocalpthcoverage. Existing primaryportable69MBarchive3fa51b91... actualrestored, usepublicanonymousdownloadandactualCPUrestoreafterReleasepublished.",
    "GitHublastpushed5dbac12; branch feat/wuji-artmanip-recovery-20260930. DraftRelease399789402/tagwuji-artmanip-recovery-20260930-v1 has59 verifiedassets, including actual-restored seed2promotion64 archive5017fe5d58e8fe5c14c3b6b9170e5d51424dfbca1ca02dd5a8a0400c3bd66877. No activeCPU sessions known.",
    "Monitor1192 remote commandlastverified17:34UTC, reverify beforestop. Remote4h17:36mean35.20percent/gap0,26passed/40targetnotmet. Need final resource integration/historyarchive andconfirmedownprocesscleanup, publicRelease+anonymousprimary/video downloads andactualrestoredCPUchecks, finalcommitpush before nativegoalcomplete."
  ],
  "bc_current_pair": "runs/artmanip-recovery-20260930/bc-pair32000",
  "training_active_runs": [],
  "bc_next_plan": "research/artmanip-recovery-20260930/bc44800-plan.json",
  "github_last_verified_commit": "5dbac12",
  "release_verified_assets": 59,
  "gpu_hours_by_host": {
    "authorized_remote": 19.983175829722207,
    "local": 0.0
  },
  "bc_executed_endpoint": {
    "path": "runs/artmanip-recovery-20260930/bc-executed44800/E/epoch_005700.pth",
    "sha256": "2f85fa6b77b9c5358d519dcd816b285efcf33900498400dd54a8ae22bba1fac3",
    "epoch": 5700,
    "updates": 45600,
    "updates_after_BC100": 44800
  },
  "current_candidate": {
    "name": "Eagg6100",
    "path": "runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth",
    "sha256": "2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8",
    "S32_passed": true,
    "S64_verified": true,
    "final_evaluated": false,
    "verification": "aggregation1-promotion64-gates.json"
  },
  "final_freeze_sha256": "881e2989c91105e4f6fd8b6b0bfa13360cab3e9cccdad5d11e0f190375d73385",
  "final_cohort_opened": true
}
```
