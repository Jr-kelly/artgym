# Wuji unified student: frozen conditional policy, strict gate not passed

One student with calibrated initial geometry/poses, legal joint/action history, FK, controller memory and external commands executes slider cycles. It does not read runtime object state. Frozen128/source final results for SA-51200 are S2[126,120,117,93] and S5[126,121,122,97]; worst strict93/128 (72.7%) is source3 S2. The full gate fails. F cycle counts[128,128,128,126] are separate from full40s body[124,106,128,110]. No hardware result is claimed.

Same-cohort teacher S2[128,127,126,105], S5[125,128,127,112] passes absolute S gates. At equal51200 updates, action-aware supervision improves7/8 strict cells and worst93/128 versus62/128 for latent-only control, with body/F tradeoffs and checkpoint-dependent development reversals. The fixed70400 endpoint and simple C1 reference are retained. No second optimization seed was triggered; this is not a convergence or seed-independent deployment claim.

The primary restore asset is **student-primary-SA51200.tar.gz**. It contains the selected encoder/Adam/RNG, fixed teacher actor, legal inference fixture, code/configs/assets and frozen evidence. Other grouped assets retain training/development history, all five final models' raw traces, actual source pins and video evidence. Restore into a fresh directory using `scripts.restore_wuji_unified`; see the branch's reproduction guide. IsaacGym and runtime dependencies are installed separately.

- [Final report](https://github.com/Jr-kelly/artgym/blob/feat/wuji-unified-student-20261001/research/unified-student-20261001/FINAL_REPORT.md)
- [Method and reproduction](https://github.com/Jr-kelly/artgym/tree/feat/wuji-unified-student-20261001/research/unified-student-20261001)
- [Teacher/student video](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/teacher-student-fixed-comparison.mp4)
- [Student video](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/student-four-sources.mp4)
- [Original failure trace](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/student-original-failure-trace.mp4)

The fixed four-state rendered comparison retains the student's source3 strict failure. It is RTX4090 resimulation, separate from H200 final statistics. Original trace animation is not a new simulation. The branch's `public-verification.json` records actual anonymous primary/video download, downloaded-code CPU restoration/input audit and full frame decoding after publication.
