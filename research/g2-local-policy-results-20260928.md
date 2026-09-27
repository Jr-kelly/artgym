# G2 + Wuji local policy: ongoing results

Status at 2026-09-28 03:12 CST: **continuous two-cycle operation has not
succeeded**. Actual PPO training is running on the local RTX4090. This is an
intermediate report, not final acceptance or a deployment result.

The new local environment restores measured full G2/Wuji/knife states from
actual acquisition runs. Only episode reset writes physical state. Its motor
interface is also available in the continuous tabletop runner, where no local
reset occurs. H holds22s; S operates20s with external5s reversals and0/+40mm
goals. A small privileged PPO controls16 support joints with bounded targets
and slew. S currently uses the original frozen teacher's thumb channel.

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

R2-03 exact endpoint maxima are **40.00/0/6.71/25.16mm**. All operation
criteria remain unchanged: last0.3s max endpoint error<10mm per phase,
full-window fixed-world drift<10mm and rotation<0.25rad, no drop/table support;
2mm endpoint score is reported separately. H and S evidence must not be mixed.

A2 was stopped and saved after finding that rotation-only early termination
omitted the remainder of the failed task from reward. A3 charges the discounted
absorbing failure cost through the original horizon; success scoring and
physics did not change. Original A2 failures and checkpoints are preserved.

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
