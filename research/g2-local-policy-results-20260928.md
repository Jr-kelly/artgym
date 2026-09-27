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

An independent full fixed-placement repeat R9-03 also passes with identical metrics (2/2 continuous runs, one geometry). Its separate raw audit passes.
The first 2969 continuous frames exactly match the previously successful real H preparation.
The frozen runtime reproduces all 600 operation commands within 1.2e-7 rad and observations within
6e-7. Fifty actual history frames are retained; the new learners are feedforward. The controller
never writes the physical knife/hand state after the initial scene setup, drives the slider,
adds an attachment or applies an external force. Full trace and source audits are in the Release.

## Frozen placement validation completed

The successful pipeline, source pin `8569f43c67817401`, H checkpoint10 and S checkpoint25 were frozen
before declaring20 new placements (seed2026092801; x/y±5mm, yaw±2°), committed as `8c4cce1`.
Manifest SHA256: `9e42be7bee055b3d5d35f6d5e536f573f1ea95547bc931ea8615847562db305c`.
All20 distinct physical placements are complete: **0/20 whole successes, 0 entered operation**.
Therefore conditional S success is **unmeasured**, not0%.

| Stage | Completed /20 |
|---|---:|
| Knife retained at end of lift | 18/20 |
| Free-space flip retained | 16/20 |
| Functional acquisition / policy takeover | 0/20 |
| Complete two-cycle pipeline | 0/20 |

The lift-stage extraction checks the complete120-frame lift and its final30 frames: knife height>0.85m,
no table contact and some hand contact each frame. It is an explicitly described diagnostic extraction;
original acquisition/operation acceptance gates were not changed. Cases04/12 left the knife on the table
before a subsequent flip-IK precheck failed. Two more cases lost retention during the flip. Of the16
retained flips,9 failed gait stability,4 support contact and3 alignment bounds. All failures remain.
Initial placements match the manifest to numerical precision; actual serialized physics matches the
fixed successful run. Planner localization uses known simulation placement, not a real perception system.

There were21 launches: case08 first failed argparse before physics on a negative scientific-notation
`--dy`; one explicitly documented retry used `--dy=<identical value>`, the same immutable source,
weights and all other parameters. The original failed launch/log is preserved. Its physical retry also
failed gait stability. The test contains20 unique geometries, not21.
See [per-placement table](g2-local-policy-validation-v1-stages.csv) and
[complete physical results](g2-local-policy-validation-v1-physical-results.json).

A separate development variant retargets the original **commanded wrist path** by a constant world
transform at the actual gait motor-reference boundary, preserving hand targets, gates and physical state.
At reused placement01 it reduces error enough to pass the former body-drift gate, but the next support
hold fails middle-finger contact (5.935mm/.1893rad body motion still passes). It is not an acquisition
success. The same predeclared variant is being checked on reused placement00. Neither reused case is
new validation. World-transform translation contains a rotation lever arm, not knife slip inside the hand.

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

Round8 completed six local diagnostics, with frozen B4cp25 and identical actual H-prepared source:

| Input / physics diagnostic | Complete S passes | Limits of the finding |
|---|---:|---|
| Fixed initial body pose + live slider q/qd | 2/2 | Body1.994/2.141mm, .1199/.1851rad; endpoints<4.4mm; still privileged slider feedback |
| Fixed initial body + slider estimated from robot FK | 1/2 | One passes; one loses slider contact at2.933s and world stability at3.633s; not reliable |
| Original privileged controller, hand gravity ON only | 0/2 | Both first unstable1.033s; same frozen controller is sensitive to omitted hand gravity |

Input variants use one ideal initial object/slider measurement. Their wrist comes from robot FK.
Independent offline replay of actual evaluations matches1200 commands per mode within1.2e-7rad;
poisoning excluded live object/wrist inputs (and slider q/qd in proprio mode) changes commands exactly0.
This confirms the implemented input removal, not deployment readiness. Acquisition and H still use
simulation truth; these are frozen-policy ablations, not a trained student.

The proprioceptive estimate assumes a fixed thumb material point with no slip. On the failed replica,
error reaches30.2mm by3.5s, before the body stability threshold; approximately29.0mm of that comes from
failure of the no-slip material-point assumption and1.14mm from ignored body motion. The successful
replica stays within2.55mm estimate error. The initial reset frame has an empty contact cache; first
contact establishes at1/30s, and it is excluded when identifying loss after establishment. This narrows
the diagnosis but does not prove all proprioceptive estimation impossible.

Gravity changes were verified on exactly26 hand bodies. No other physical parameter changed.
The bounded motor-only gravity-feedforward S comparison R10-01 now independently passes2/2 under hand gravity ON:2.658/2.664mm and .10852/.10636rad; endpoints<3.5mm, strict2mm fails. H comparisons and continuous promotion remain pending. Controller:
URDF modeled gravity divided by actual PD stiffness, target bias capped±.08rad, original total target
slew/joint limits retained. Offline torque agrees independent potential-energy derivatives; initial
required bias is≤.06344rad and fits original limits. These are model torques, not measured forces.

Baseline hand gravity is OFF; G2 arm gravity is ON. Original servo, collision filtering, friction,
masses and freely sliding knife joint are unchanged and uncalibrated on hardware. No real detent/lock
force has been measured. These constraints materially limit sim-to-real claims.

## Evidence and continuation

- [Branch](https://github.com/Jr-kelly/artgym/tree/feat/g2-wuji-local-policy-20260928)
- [Release: full continuous and close-up videos, models, raw evidence](https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-local-policy-20260928-v1)
- [Full successful video](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-local-policy-20260928-v1/tabletop-pickup-flip-learned-H-S-two-cycles-full.mp4)
- Local browser: http://127.0.0.1:8767/g2-local-policy-20260928/
- [Reproduction commands](g2-local-policy-reproduction-20260928.md), [full preregistration/journal](g2-local-policy-20260928.md), [control ledger](g2-local-policy-control-results-20260928.csv)

Next: finish the bounded gait-coordinate comparison and independent fixed continuous repetition;
then the preregistered motor-only gravity comparison. No fifth training configuration. Any changed
method requires a newly declared test set before a new-placement success claim.
