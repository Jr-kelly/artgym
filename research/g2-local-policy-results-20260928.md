# G2 + Wuji local policy: ongoing results

Status at 2026-09-28 04:28 CST: **continuous two-cycle operation has not
succeeded**. Actual PPO training ran on the local RTX4090; B4 is now saved and stopped after two regressive evaluations. Frozen control diagnostics continue. This is an
intermediate report, not final acceptance or a deployment result.

The new local environment restores measured full G2/Wuji/knife states from
actual acquisition runs. Only episode reset writes physical state. Its motor
interface is also available in the continuous tabletop runner, where no local
reset occurs. H holds22s; S operates20s with external5s reversals and0/+40mm
goals. A small privileged PPO controls16 support joints with bounded targets
and slew. The earlier S support route uses the frozen thumb teacher; current B4 jointly controls all20 hand joints around a geometric thumb motor prior.

| Comparison | Evidence | Interpretation |
|---|---|---|
| Continuous fixed motors H, old identical prefix | 2.617mm /0.5922rad | Fails rotation |
| Continuous learned H, R2-04 | 0.620mm /0.01554rad; slider0.038mm;22s; no table contact | H passes after real table pickup and flip |
| Fresh local learned H, R2-01 | 4/4 H passes, one acquired state | Reset repeatability, not new-placement generalization |
| H training selection, A1 main10 | 31/32 basic H;25/32 slider2mm | Development replicas, not independent geometries |
| Learned first output held constant, R3-01 | 0.682mm /0.02567rad; slider0.120mm;22s | Fixed learned targets suffice for local H; feedback superiority unproven |
| Full frozen teacher S, R2-05 | 44mm /3.131rad; slider travel4.657mm | Actual-acquired-state failure baseline |
| H support learner + frozen thumb S, R2-03 | 18.47mm /0.964rad; endpoints40/0/6.71/25.16mm | H success does not transfer to S |
| S support training A2 eval25 | 0/32; median22.818mm /1.2146rad | Some body improvement, no successful two-cycle operation |
| Closed-goal5s preparation, R3-02 | 79.888mm /3.029rad; slider goes to50mm | Preparation fails; later stationary knife is not whole success |
| Faster first-stroke thumbq4, R3-04 | Travel0.718mm;28.6mm /0.902rad | Speeding onlyq4 does not fix the articulation problem |
| Coordinated geometric thumb path + fixed learned support, R3-05 | 2.221mm /0.0853rad body;12.389mm slider travel; all extension endpoints fail | Holds body, loses thumb-slider contact around1.5–2s |
| Same thumb path + live Hsupport, R3-06 |301.5mm /3.118rad; drops; unstable by11s | Hfeedback transfer can itself fail |
| B4 joint PPO update10 | **2/32 local Spasses,1/32 strict2mm**; both thumb contact100%, table0 | First learned two-cycle coordination; fragile and not continuous acquisition |
| B4 update25 | **4/32 local Spasses**, independently rescored; strict0/32 | Basic success improved; one acquired source only |
| Fresh simulation of B4update10, R4-01 | **0/4** across2envs×2resets | Selected training-evaluation success does not establish repeatability |

R2-03 exact endpoint maxima are **40.00/0/6.71/25.16mm**. All operation
criteria remain unchanged: last0.3s max endpoint error<10mm per phase,
full-window fixed-world drift<10mm and rotation<0.25rad, no drop/table support;
2mm endpoint score is reported separately. H and S evidence must not be mixed.

A2 was stopped and saved after finding that rotation-only early termination
omitted the remainder of the failed task from reward. A3 charges the discounted
absorbing failure cost through the original horizon; success scoring and
physics did not change. A3eval25 remains0/32 with median24.6mm/1.213rad;
this support-only S route was stopped. Original failures and checkpoints are
preserved. B4 is the fourth and final training configuration: privileged PPO
joint20 residuals around the measured geometric thumb path, starting on the
local4090 at03:28:55. It is a new controller; the original thumb teacher is
now a comparison rather than part of this route. Independent raw scoring
confirms the two local successes:4.470mm/0.19368rad with endpoint maxima
1.636/1.592/0.779/1.179mm, and0.915mm/0.10475rad with endpoint maxima
0.231/2.355/0.035/2.007mm. All30 failures remain in the denominator.
The first fresh-simulator repetition failed4/4. The later checkpoint25 passed
4/32 local development replicas. Continuous R4-02 failed after successful pickup:42.420mm/3.09654rad, first instability2.8s, endpoints37.203/2.527/38.686/.703mm. No table-to-operation success
or unseen-placement validation is claimed.

The [control ledger](g2-local-policy-control-results-20260928.csv) separates
local resets, continuous holding, software-aborted diagnostics and failures.
Training evaluations are separate model-selection data, not additional
independent placements. The completed baseline evidence and failure videos are
in [Release v1](https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-local-policy-20260928-v1);
active B4 and subsequent continuous checks will be delivered as another increment.

All new local networks use real-time simulated object pose, velocity and slider
state. The composite is a **new privileged method**, not unchanged teacher
success or a deployable student. Hand gravity remains disabled as in the
frozen baseline; G2 servo, collision filtering and free slider are unchanged
and have not been calibrated to a real knife or robot.

Code: `feat/g2-wuji-local-policy-20260928`. Commands are in
[reproduction](g2-local-policy-reproduction-20260928.md); detailed preregistration
and chronological evidence in [journal](g2-local-policy-20260928.md).
Machine recovery state is `runs/g2-local-policy-20260928/state.json`.
No new-placement acceptance set or student success is claimed.

Continuous handoff audit confirms all2309 prefix frames and q/qd, knife/slider state, targets, integral and50-frame history exactly match the source. It found a first-observation quaternion **sign** difference: equivalent wrist rotations cause different uncanonicalized network input. Optional first-frame compatibility matches the frozen local first action within3e-8; R4-03 tests ONLY this representation change. No physical pose reset, new weight, changed limit or fifth training configuration. Independent eval50 gives2/32; eval75 gives0/32. B4 stopped after76 completed updates,155776 sampled transitions,1462 ended training episodes and2485.67s including evaluation. All4 major configurations have been used; no fifth is started.

Round5 predeclares at most6 control executions: two fresh local cp25 runs, then two open-loop replays of successful replica5 motor targets. The replay carries only600 hand command offsets at30Hz, checks original limits and .02/.025rad per-step bounds, and anchors to actual initial motor references. It neither loads measured joint/object poses nor drives the slider. This comparison is a control baseline, not live teacher/student success. Continuous replay is conditional on local evidence.

Later continuous input-compatibility test R4-03 still failed44.44mm/2.983rad despite exact first command; the sign mismatch is not sufficient to explain the failure. Freshcp25 and successful open-loop command replay both0/2. Contact-normal feedback0/2; fullpoint feedback0/2whole, although one replica passed allfour endpoints (1.311/<.001/3.042/0mm) while11.065mm/.998rad body drift failed. No threshold changed. R7 now evaluates the **actual** previously successful continuous22sH final state as a different support initialization, with the same frozen S weights; this remains local development, not new-placement generalization.

**New actual H-prepared state: R7-01 independently passes2/2 local S.**
Same frozen B4cp25, but initialization is the actual end of the previously
continuous H22s+2ssettle run. Maxworld2.145/2.038mm, rotation.19285/.17283rad;
fourphase endpoint errors all<4.5mm (2mm strict fails). One placement, a
second actually reached support state, no fabricated pose. Runtime replay
600frames maxmotorerror1.2e-7rad; firstbodyjump.108mm. R7-03 now executes
actual tabletop→H22s→S20s without resets; result pending. R7-04 checks
one fresh environment across two local resets. Planned alternative controller
is skipped to concentrate on the learned method. No new training configuration.
