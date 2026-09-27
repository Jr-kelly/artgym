# G2 + Wuji local policy: ongoing results

Status at 2026-09-28 03:44 CST: **continuous two-cycle operation has not
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
| Faster first-stroke thumbq4, R3-04 | Travel0.718mm;28.6mm /0.902rad | Speeding onlyq4 does not fix the articulation problem |
| Coordinated geometric thumb path + fixed learned support, R3-05 | 2.221mm /0.0853rad body;12.389mm slider travel; all extension endpoints fail | Holds body, loses thumb-slider contact around1.5–2s |
| Same thumb path + live Hsupport, R3-06 |301.5mm /3.118rad; drops; unstable by11s | Hfeedback transfer can itself fail |
| B4 joint PPO update10 | **2/32 local Spasses,1/32 strict2mm**; both thumb contact100%, table0 | First learned two-cycle coordination; fragile and not continuous acquisition |

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
Fresh-simulator repetition and continued training are ongoing.

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
