# G2 + Wuji local policy results — ongoing

**The fixed continuous tabletop task passes (R7-03). Generalization and deployable inputs remain unproven.**
This is a newly learned privileged H→S controller, not the unchanged original teacher or student.
The full uncut 118.967 s run performs normal flat slider-down pickup, approximately 180° air flip,
finger gait, learned 22 s holding, 2 s actual settling/history, then 20 s operation with two cycles.

| Independent fixed-run measurement | Result |
|---|---|
| Four final-0.3 s maximum endpoint errors | 4.145 / 0.001024 / 4.086 / 0.000030 mm |
| Full-operation fixed-world body motion | 2.115 mm / 0.172077 rad |
| Basic endpoint <10 mm AND world <10 mm / 0.25 rad | Pass |
| Strict 2 mm endpoints | Fail on extension |
| Drop / table support during operation | None |
| Thumb–slider contact | All 600 operation frames |
| Independent 22 s preparation H | 0.620 mm / 0.01554 rad; slider movement 0.038 mm |
| Local S repeats from actual H-prepared state | 4/4, one placement; not four geometries |

The first 2969 continuous frames exactly match the previously successful real H preparation.
The frozen runtime reproduces all 600 operation commands within 1.2e-7 rad and observations within
6e-7. Fifty actual history frames are retained; the new learners are feedforward. The controller
never writes the physical knife/hand state after the initial scene setup, drives the slider,
adds an attachment or applies an external force. Full trace and source audits are in the Release.

## Current validation

The successful pipeline, source pin `8569f43c67817401`, H checkpoint10 and S checkpoint25 were frozen
before declaring 20 new placements (seed 2026092801; x/y ±5 mm, yaw ±2°), committed as `8c4cce1`.
The manifest SHA256 is `9e42be7bee055b3d5d35f6d5e536f573f1ea95547bc931ea8615847562db305c`.
The running test is unchanged. Early failures occur in flip IK or finger-gait stability/contact,
before operation; they cannot identify how the S policy would perform after a valid acquisition.
Planner localization uses known simulation placement, so this is placement variation, not perception robustness.

One case failed before physics because argparse rejected a negative scientific-notation `--dy` value.
Its log is retained. An explicitly identified retry will use `--dy=<same value>` with the same frozen
code/controller. Report the failed launch separately from the 20 unique physical placements.
Read the final machine-readable validation results before quoting a success rate; the set is still running.

Read-only code inspection found absolute nominal arm joint targets in the gait. A bounded geometric
retargeting diagnostic preserves the actual motor-reference start and transforms the original wrist
path. Initial nominal/failed-case screens pass IK and arm/table checks, but this has **no physical
success evidence yet** and does not alter the frozen test. World-transform translation includes a
rotation lever arm; it is not the distance the knife must slide in the hand.

## Relevant comparisons

| Comparison | Result and supported inference |
|---|---|
| Original full teacher, actual acquired local S state | 44 mm / 3.131 rad; fails |
| Fixed motor H after same continuous prefix | 0.592 rad rotation; fails |
| Learned H, continuous | 0.01554 rad; passes |
| First learned H output held constant, local | 0.02567 rad; passes; feedback superiority not established |
| H support learner + original teacher thumb S | 0.964 rad; H alone does not transfer to S |
| Geometric thumb prior + fixed learned support | Body passes; 12.39 mm travel then contact loss; extension fails |
| B4 joint PPO selected cp25, old local source | 4/32 development replicas; fresh repeat 0/2 |
| Continuous B4 old source, exact first-observation fix | 44.44 mm / 2.983 rad; quaternion fix alone insufficient |
| Successful command-sequence motor replay | 0/2; command sequence alone fragile |
| Privileged contact-normal / full-point correction | 0/2 each; one full-point run meets endpoints but 11.07 mm / 0.998 rad fails stability |
| Same B4 after physically executed H preparation | 4/4 local repeats and one complete continuous pass |

The H-prepared source is a recorded real continuous state, not an interpolated or cached pose injected
into the continuous task. Compared with the old S source, body pose differs by 0.576 mm / 0.03875 rad
and support motor references by up to 0.01971 rad. This narrows attention to support initialization and
coordination; it does not establish a unique causal mechanism.

## What was trained

Local full-G2 Isaac Gym / GPU PhysX environments restore a documented actually reached state only at
training/evaluation reset. These resets are labeled local, never tabletop success. Two routes and all
four major configurations were used: A1 learned 16-joint holding, A2 learned support with frozen teacher
thumb, A3 corrected an early-termination reward shortcut, B4 learned a bounded 20-joint residual around
a geometric thumb motor path. Reward and independent success scoring are separate.

B4 uses 32 environments, 128×128 MLP/PPO, horizon64, epochs4, minibatch2048, learning rate3e-4,
gamma0.995 and lambda0.95. It completed76 updates /155,776 sampled transitions /1,462 ended training
episodes in2485.67 s including evaluation. Evaluations at10/25/50/75 passed2/4/2/0 of32 replicas;
training was stopped and saved after regression. No fifth major training configuration is started.
Selected checkpoints are A1-H-pilot10 and B4-S-joint-path25. All old models and failures remain.

## Input pipeline and limitations

Actual robot q/qd, command targets, fixed takeover references, external clock and previous policy
outputs join **live simulated knife pose/velocity and slider state** as policy inputs. H adjusts
16 support targets; S adjusts20 targets around the thumb prior. Outputs are robot motor targets only:
residual span±0.20 rad, slew0.60 rad/s, total thumb increment≤0.025 rad/control, original joint limits.
The G2 arm servo and its integral state persist through every stage.

Round8 is preregistered for six local executions without training: two fixed-body/live-slider input
ablations; two one-time ideal initialization plus proprioceptive slider estimates; two privileged S
runs with hand gravity enabled as a separate physical sensitivity. They wait for the frozen validation.
Offline on the known success, thumb-point FK predicts slider position within2.264 mm maximum;
this is neither a closed-loop test nor a deployable result. The estimator assumes stationary body and
no contact slip. Robot/FK and quaternion input checks pass; physical results remain pending.

Baseline hand gravity is OFF; G2 arm gravity is ON. Original servo, collision filtering, friction,
masses and freely sliding knife joint are unchanged and uncalibrated on hardware. No real detent/lock
force has been measured. These constraints materially limit sim-to-real claims.

## Evidence and continuation

- [Branch](https://github.com/Jr-kelly/artgym/tree/feat/g2-wuji-local-policy-20260928)
- [Release: full continuous and close-up videos, models, raw evidence](https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-local-policy-20260928-v1)
- [Full successful video](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-local-policy-20260928-v1/tabletop-pickup-flip-learned-H-S-two-cycles-full.mp4)
- Local browser: http://127.0.0.1:8767/g2-local-policy-20260928/
- [Reproduction commands](g2-local-policy-reproduction-20260928.md), [full preregistration/journal](g2-local-policy-20260928.md), [control ledger](g2-local-policy-control-results-20260928.csv)

Next: complete all frozen placements, separate acquisition failures from conditional operation,
then execute the preregistered input/gravity diagnostics. Any changed gait must be explicitly separated
from this frozen test; current test placements become development data if reused.
