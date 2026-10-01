# Wuji unified student — active experiment

This round asks whether a single encoder using available joint/action history and calibrated initial object information can replace Eagg6100's runtime privileged encoder while preserving closed-loop knife-slider control. Training and model selection are still active; no final student claim has been made.

| Evidence | S2 strict per source | S5 strict per source | Body / scope |
|---|---|---|---|
| Restored Eagg6100, new development32 |32,32,32,24 /32|32,32,32,29 /32|All S body32/32; source3S2 below80% screening threshold|
| Eagg6100, independent confirmation64 |63,63,64,56 /64|Pending|Restored teacher supported; retain lower development result|
| Eagg6100, new development F |32,32,32,32 /32 complete cycles|Separate40s protocol|Full40s body32,22,27,30 /32; functional success is not full-horizon stability|
| Legal-input S0 preflight |No capability evaluation|No capability evaluation|16 real Adam updates; dummy privileged perturbation leaves action and all RNN unchanged; frozen actor/normalizer hashes unchanged|
| Student C0/C1/S0 |In progress|In progress|Initial-calibration-conditional, not pure proprioceptive autonomy or hardware success|

Teacher recovery initially used the evaluator's wrong default actuator (`wuji_paper`). Those two failed runs are retained as engineering failures. The restored original profile is explicitly `wuji_paper_official_actuator`, fixed original-axis bridge3 asset, .04rad support span, .025rad thumb increment,30Hz. New data use the original grasp-neighbourhood perturbations, with historical final rows excluded by hash. The old final set is closed; new final is not used in development.

H200 batch5/128 fixed-slot checks agree on strict outcomes `[pass,pass,pass,fail,fail]` for old development rows `[0,32,64,96,97]`. H200 camera creation failed. On the already-authorized RTX4090 the no-render/render pair completes, and the row96 boundary changes to pass. Neither these repeated states nor rendered reruns add independent samples. H200 stays the primary statistical environment. Replacing simulator tip origins by URDF FK changes positions by about5µm, yet some long-horizon boundary outcomes also change; portability has not been established.

Method: calibrated initial55 +50×(q20,previous-action20) → repository temporal encoder → frozen actor → original mixed controller. The actor additionally receives current q, previous action, external command and realizable fingertip FK. Current object pose/slider state/contact/physics truth are zeroed before the student player, including the critic recurrent path. Teacher labels are used only for training or independent comparison. C0 is one global mean latent; C1 maps initial55 to a constant latent. See [INPUTS.md](INPUTS.md) for the entire execution interface and unverified initial-calibration requirements.

S0 resumes the16-update preflight with actual Adam/RNG to cumulative3200 updates; C1 receives3200 updates. Each update collects4 transitions in256 environments (1024 interactions). Only the encoder updates. Linear teacher-latent warm start ends at400 absolute updates (12.5% of the minimum budget), then behavior is purely student; all evaluations use zero mixing. Checkpoints400/800/1600/3200 are queued for independent S2/S5/F evaluation; longer training and at most two controlled repairs require recorded evidence. Resume starts new physical episodes because PhysX state is not serialized.

Budget begins2026-10-01 06:03:30UTC, ends22:03:30UTC;64GPUh maximum, at most4 simultaneous jobs, ordinary cutoff20:33:30UTC and6GPUh reserved. This is a ceiling, not a consumption target. Current PIDs, source/config/weight hashes, receipts and continuation instructions are in [STATE.json](STATE.json), [HANDOFF.md](HANDOFF.md) and [DECISIONS.jsonl](DECISIONS.jsonl). Process facts are timestamped and must be rechecked.

The branch is [feat/wuji-unified-student-20261001](https://github.com/Jr-kelly/artgym/tree/feat/wuji-unified-student-20261001). Final reports, frozen model selection and a separate downloadable Release will be added after experiments finish. No old Release is modified.
