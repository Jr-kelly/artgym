# Restore/run the geometry round

Use `feat/wuji-geometry-generalization-20261002`, based on the completed student branch e6c9f3e. Previous final cohorts/releases are closed and unchanged. This is a new geometry research round with cumulative64GPUh, historical32.4534053852823GPUh and6GPUh final reserve; there is no old wall-clock deadline. No hardware is connected.

Clone this public branch without `--recurse-submodules`: the legacy `func_lygra`/`make_data` SSH submodules are not needed by this geometry runtime; `rl_games`, baseline hand assets, quaternion reference caches and default training seeds are already tracked in the main tree. Restore this round's `geometry-frozen-parent-models.tar.gz` and `geometry-controlled-assets-v1.tar.gz` with `scripts.restore_wuji_unified` into the isolated checkout. These provide the exact frozen teacher/SA51200 Adam/RNG, generated controlled assets and new split datasets. Never overwrite different existing artifact bytes. Additional final candidate/evidence bundles are listed in the final release manifest. The previous primary bundle remains preserved as an optional historical reference; it is not required for this new restoration chain.

Scientific runtime is Python3.8/PyTorch2.1.0+cu118 with IsaacGym TacSL. Import IsaacGym beforeTorch. Supply a compatible driver/runtime independently. Use the complete runtime prefix:

```bash
export PATH=/path/to/runtime/bin:$PATH
export LD_LIBRARY_PATH=/path/to/runtime/lib:$LD_LIBRARY_PATH
export PYTHONPATH="$PWD:$PWD/rl_games"
export PYTHONNOUSERSITE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2
export CUDA_VISIBLE_DEVICES=0
```

Controlled assets use URDFwidth,thickness,length and transformed publicbboxwidth,length,thickness. `BASELINE_PHYSICS.json` is the measured original actor mass/inertia/joint parameter reference. `WujiGeometry` freezes effective inertia afterIsaacGym's automatic shape-based inertia calculation, with recompute=False. Keeping authoredURDFinertia alone is insufficient. Slider size/travel/physics/control remain unchanged. Length is centered; thickness shifts jointY by half thickness difference.

`prepare_wuji_geometry` registers13conditions, preserves copied zero-changeURDF, generates contactIK seeds and disjoint new perturbations. Run only in a fresh checkout/output namespace; it refuses to overwrite assets. Existing prepared datasets should be restored, not regenerated in place. `grasp_state_metadata.json` must declare hand_base poses. Ignoring this metadata places the object in the wrong world position.

```bash
/path/to/runtime/bin/python -m scripts.static_wuji_geometry \
  --label T90 --split screen-attempts --take 16 --output runs/my-T90-static
/path/to/runtime/bin/python -m scripts.evaluate_wuji_geometry \
  --label T90 --states runs/my-T90-static/valid-states.npy \
  --model teacher --protocol S2 --output runs/my-T90-teacher-S2
/path/to/runtime/bin/python -m scripts.evaluate_wuji_geometry \
  --label T90 --states runs/my-T90-static/valid-states.npy \
  --model student --protocol S2 --output runs/my-T90-student-S2
```

The accepted states are chosen by registered geometry/static rules, never teacher/student success. Pair the exact same states file. Missing sources are adaptation coverage gaps, not0%policy success; no batch padding enters denominators.

S2/S5:20s, fixed external2/5s clock, every stage's final9samples <2mm, fullvalidity and bodytranslation<10mm/rotation<.25rad. F:40s, originaltrue-slider arrival scheduler (<10mm for45samples), at least one complete open-close cycle; fullbody stability separate. F does not establish sensor-free autonomous arrival detection.

Each remote job receives a copied immutablepin and bounded timeout, a command/source/model identity, stdout, start/end/exit andGPUtime receipt. Source can change locally during analysis without mutating runningpins. `wuji_geometry_jobs` and queues are specific to the presently user-authorized host; historical host addresses do not grant authorization to other operators. User can run the direct scientific commands elsewhere with equivalent prerequisites.

CPU rescoring and interface verification:

```bash
CUDA_VISIBLE_DEVICES='' /path/to/runtime/bin/python -m scripts.analyze_wuji_geometry \
  --runs runs/geometry-generalization-20261002 --prefix screen- \
  --output research/geometry-generalization-20261002/screen-analysis
CUDA_VISIBLE_DEVICES='' /path/to/runtime/bin/python -m scripts.audit_wuji_geometry_runtime \
  --output research/geometry-generalization-20261002/offline-runtime-audit.json
```

The analyzer independently recomputes endpoint/Fcycle/body results and compares recordedcounts; emits per-episodeCSV, per-geometry/source/protocol Wilson95 and paired transitions/bootstrapdifferences. Geometry/source macroaverages include complete coverage explicitly and retain missing-source conditions separately. Shared cross-geometry perturbation lineage is paired where selectedattempt rows overlap, while adapted physicalstates are different.

The SA interface `WujiTemporalPolicyRuntime.reset/step` consumes initialq, initialbody/sliderposes, two rawURDFbboxes andinitialissuedtargets. Runtime inputs are measuredq, externalgoal and knowncontroller memory; it maintains50step history, previousaction, issuedtargets andRNN, with partialreset. It usesFK, no currentobject/slider/contacttruth. `applied_previous_action` and `issued_previous_targets` support replay of commands actually sent by a driver. Output is action/jointtargets only; this module never commands hardware. The command generator remains external.

Initial/static assets, train fit, frozen physicalscreen, independentconfirmation/final, CPUparity and separately rendered resimulationvideos are distinct evidence categories. Old finals must not be opened for new model/grasp selection. Current HANDOFF/STATE/DECISIONS identify which new phases are complete; this document does not claim pending phases have passed.
