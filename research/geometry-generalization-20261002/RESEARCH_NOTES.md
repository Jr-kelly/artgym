# Geometry round research notes

The attachment is the operative user-authorized goal. Old teacher/student final cohorts remain closed. Previous successful acquisition/flip demos and all prior releases are preserved.

The13initial conditions useL147/W19/T8mm and one-axis0.8/0.9/1.1/1.2 ratios. Slider dimensions/travel/control remain fixed. Thickness necessarily moves jointY by half thickness difference. Length is centered with fixed longitudinal joint origin. Grasp IK is local and policy-independent.

Two-second static acceptance checks finite state/joint limits, baseline-relative vertex-SDF penetration allowance(+1mm), drift<10mm, rotation<0.25rad and no invalid/fall. The penetration estimate is a geometry proxy and does not certify exact whole-hull separation. All attempted/valid/rejected rows are retained. Manipulation pairs use exactly the same accepted rows; source counts may differ, and no padding enters the denominator.

Initial cache frame metadata omission produced a50mm fall in3steps for all baseline/T90 rows. Those first results are infrastructure failures and archived; hand_base metadata and an effective-frame assertion repair it. Separately IsaacGym overrides authored URDF inertia from box density, so all changed conditions now explicitly freeze measured baseline actor inertia. Early unfixed-inertia statics are supplementary, not the final controlled experiment. Baseline physical preflight had the correct measured inertia and remains valid.

The no-hardware SA reset/step interface was compared with original player/history/controller methods on80nonconstant CPUsteps, four slots, baseline/T90/W120 and two partial resets. Same applied-action/issued-target replay passes: maxaction1.14e-5, target4.77e-7rad, RNN1.51e-4. Separate independently propagated command streams had action3.46e-5 and target2.50e-6rad differences; these remain a finite-precision diagnostic, not physical evidence. The runtime only uses initial calibrated poses/bboxes, q, FK and known external command/memory. No runtime object/contact/slider truth and no hardware commands.

Baseline screening is new16valid rows/source. Teacher S2 success60/64, fullbody63/64; SA S2 success57/64, fullbody64/64. This small screen neither replaces old final results nor proves a gate. Initial changed-length checks show missing source3 coverage (L80/L110/L120 none, L90 only2valid rows); classify adaptation failure, not policy0%. No branch selected and no new optimization yet. Await full S2/S5/F screen and independent64confirmation before selecting the primary branch.
