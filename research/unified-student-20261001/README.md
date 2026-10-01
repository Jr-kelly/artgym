# Wuji unified student: cycling works, strict source3 stability remains unresolved

The frozen primary is **SA-real-51200**, SHA256 `16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9`. It replaces runtime privileged latent estimation with one conditional student encoder and the fixed Eagg6100 actor. **The full gate fails.** This is an executed negative capability result, not a deployment or convergence claim.

## Frozen final evidence

Each count is out of128. Five models and three protocols share the same512 new initial states; stages, repeated models and protocols do not enlarge independent-source denominators. All7680 protocol episodes were independently rescored, and all60 model/protocol/source cells passed the [coverage and provenance audit](final-integrity.json). [FINAL_REPORT.md](FINAL_REPORT.md) gives Wilson95% intervals, paired transitions, all gates, stage holds and failure times; [episode CSV](final-analysis/trials.csv) preserves unfiltered trials.

| Policy | S2 strict, sources 0/1/2/3 | S5 strict, sources 0/1/2/3 | Minimum S2 / S5 body stability |
|---|---|---|---|
| Eagg6100 teacher | 128,127,126,105 | 125,128,127,112 | 125 / 125 |
| SA-51200 selected student | 126,120,117,93 | 126,121,122,97 | 121 / 124 |
| SA-70400 fixed endpoint | 114,108,113,94 | 106,97,83,84 | 120 / 122 |
| SC-51200 equal-update latent control | 120,119,115,77 | 115,123,117,62 | 124 / 124 |
| C1 initial-only reference | 0,0,0,0 | 0,0,0,0 | 0 / 0 |

Only source3 fails the primary S gates. S2 strict93/128 is below80%, body121/128 is below95%, and the body loss to teacher is3.125pp (>3pp). S5 strict97/128 is below80%, and the strict loss to teacher is11.719pp (>10pp). Same-cohort teacher passes all absolute S thresholds; its failures remain in every paired comparison. Gate decisions use observed proportions, not confidence lower bounds.

Primary F cycle counts are[128,128,128,126]/128. Full40-second body stability is[124,106,128,110]/128, including a separate source1 stability gap. F's arrival-based external command scheduler reads true slider state; the policy sees only the issued command. These results do not establish a sensor-free autonomous arrival detector.

Source3 S2 has28 full-body-stable endpoint failures and7 body failures; all28 stable failures miss an opening hold, and one also misses closing. S5 has27 stable opening failures and4 body failures. Among stable source3 failures, the median first missed stage is5 in S2 and1 in S5. Among body failures, median first breach is5.37s and3.15s respectively. These locate the loss; they do not prove its cause. The final cohort is now closed and may not be used for further tuning.

## Method and controlled evidence

Calibrated initial55 +50×(q20, previous-action20) +21 known controller fields → repository temporal encoder → frozen Eagg6100 actor/normalizers → original mixed controller. The actor's public inputs also include external target and URDF fingertip FK. Initial target memory comes from issued reset commands, not measured q. Support targets are initial targets+.04×action; thumb targets accumulate+.025×action with the original limits. See [INPUTS.md](INPUTS.md) for dimensions, frames, normalization and unverified hardware sources.

Raw runtime privileged fields111:137 are masked before the whole student player, including the recurrent critic path; raw137 is fixed SAPG coefficient50, not a source identifier. Frozen nonconstant-sequence perturbations preserve actions and all RNN state exactly. Actor teacher-encoder calls are zero. No expert switching, privileged latent mixing, drop-triggered takeover or actor retraining occurs in evaluation.

S0 completed3200 actual Adam updates. Two evidence-triggered repairs followed: adding controller memory with a same-width masked-input control, then executed-target supervision with an equal-update latent-only control. SA loss is latent MSE +25×executed-target MSE/(.04rad)², using the exact forward controller target and an explicit straight-through backward surrogate. Both counterfactuals share incoming RNN; only the live behavior advances recurrent state. Each update collects4 transitions in256 environments, or1024 interactions. Teacher mixing ends at absolute update400; later behavior is entirely student. Continuations restore Adam/RNG and start declared new physical episodes.

At the matched51200 counter (shared SC6400 parent), SA improves7/8 final strict cells and worst strict93/128 versus62/128 for SC; source3 improves77→93 in S2 and62→97 in S5. SA is worse on source1 S5 and some body/F cells. [Controlled development history](controlled-method-summary.json) retains reversals at other budgets, so this is not a uniform or seed-independent advantage. Tested C0/C1 strict performance is poor; this does not rule out every possible constant-latent method.

Both existing methods continued through70400. Late SA44800/48000/51200 improvements were followed by tradeoffs and regression; the fixed SA70400 final worst strict is83/128. We retained the development-best, endpoint and equal-update control before final access. The last window ended to preserve the registered final-delivery reserve, not because a short strict plateau proved convergence. No development candidate met the preregistered full/one-episode confirmation rule, so no student confirmation, second optimization seed or conditional robustness campaign was triggered.

## Limits and next experiment

This student needs precise initial calibration whose real acquisition is not established. There is no real-hand test, autonomous grasp acquisition, unseen knife/grasp generalization, independent runtime implementation or latency qualification. The CPU whole-player audit reuses the evaluated implementation; it is not an independent deployment stack.

H200 camera creation failed; local RTX4090 teacher checks retain hardware/batch sensitivity near a boundary. One instrumented SA28800 diagnostic changes the first action, whereas its uninstrumented repeat exactly matches the original. Instrumented labels are not attributed to the original run. An original source3 development stall is also present in the fixed teacher. These observations do not prove observability failure or explain all remaining losses. [Research notes](RESEARCH_NOTES.md) preserve the diagnostics and uncertainties.

A next round should first register a fresh optimization RNG repeat of the same action-aware method and its equal-update control, with new development/confirmation states, to test whether the selected-checkpoint benefit persists. Only then test a single stage-focused learner-state replay factor from a common parent if opening-hold failures persist. The current final set stays closed. Changing `--seed` alongside `--resume` alone is not a new RNG seed.

## Reproduce and distribution

[REPRODUCE.md](REPRODUCE.md) describes runtime prerequisites, training, restoration and independent scoring. [Freeze](final-freeze.json), [data manifest](data/manifest.json), [learning curves](figures/source-learning-curves.png), [fitting curves](figures/source-fitting-curves.png), [journal](DECISIONS.jsonl) and [durable state](STATE.json) retain actual commands and hashes. Start/deadline remain06:03:30/22:03:30UTC on2026-10-01. GPU computation used32.453405 hours, with at most4 concurrent jobs; all owned GPU tasks and the verified monitor stopped, and ToDesk remains ([resource receipt](resources-final.json)).

The [separate Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-unified-student-20261001-v1) contains the primary restoration bundle, training checkpoints with Adam/RNG, raw development/final traces, actual pinned source history and videos. The primary bundle is `student-primary-SA51200.tar.gz`; IsaacGym and the compatible runtime must be installed separately. [Public verification](public-verification.json) passed at2026-10-01 20:15:13UTC: the primary archive and all four videos were actually downloaded without authentication,4246 files restored, downloaded code executed, encoder/Adam/RNG and whole-player input checks passed, and all four600-frame videos decoded. Restored source, input definition and cohort hashes match the freeze. GitHub anonymous metadata was rate-limited; metadata used the existing operator credential, while file downloads remained anonymous. The original failures and the retained verification helper make this distinction explicit.

- [Student, four fixed development states](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/student-four-sources.mp4): strict[pass,pass,pass,fail], body all pass.
- [Teacher/student same-state comparison](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/teacher-student-fixed-comparison.mp4): teacher all pass; student source3 failure retained.
- [Original failure trajectory](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/student-original-failure-trace.mp4): deterministic first failed development episode, source0 trial23; original H200 arrays, no physics rerun.

All videos are20 seconds/600 frames. Rendered examples are separate RTX4090 resimulations and never replace H200 final statistics or add samples. [Video manifest](video-manifest.json) retains hashes, conditions and the presentation-only failure-plot layout correction.
