# G2 + Wuji v1 contact transfer, 2026-10-06

The retained nominal1.25N demo exactly reproduces24.366mm active travel with
continuous pickup,1s hold and cap contact1.0. Its trace hash equals the previous
delivery. One NEW joint validation combines changed mid geometry with1.25N,
one30Hz-frame actuation delay, noise/bias:22.123mm passes. This extends evidence
at the retained capacity; there is no validated new capacity above1.25N and no
measured maximum thrust. Reference0.7355N and previous1.5N failures remain in
singlepush-v1; they were not reswept or repackaged as new achievements.

## Implemented and independently checked

- Central name-derived20-joint mapping fixes the ring/pinky swap. SIM blocks are
  index/middle/pinky/ring/thumb; SDK thumb/index/middle/ring/pinky. Conversion
  [4,0,1,3,2], inverse[1,2,4,3,0].20 distinct values roundtrip and three actual
  saved postures pass. All new20-joint exports carry names, units and source.
- Independent finite-difference Jacobian agrees with analytic world Jacobian to
  <1.2e-10m/rad at start/middle/end. Virtual work is invariant under world/knife
  transforms. A downward external load on a+Z hinge at+X requires a positive
  motor torque, disproving the old plus sign under the declared convention.
- `reaction=Rknife@[0,normal,-axial]` acts ON the hand; prior upward gravity term
  is gravity compensation. Therefore motor=inertial demand+gravity compensation
  −Jᵀreaction. Recomputed saved1.25N trace covers p05/mean/peak normal assumptions
  and0.7355/1/1.25/1.5N assumed axial loads. Worst modeled fraction changes from
 44.24% to38.79%; old conclusion withdrawn. Signed external/gravity/dynamic/motor
  terms and raw simulation motor values are retained. Raw motor signs match all
  four contact-compensation joints at20.1s; earlier mismatch is retained because
  actual contact points/axial totals, multi-link reactions and transients are not
  measured by this simplified marker model. No forced numerical equivalence.
  Thumb4 actual position boundary remains; a modeled effort reserve gives no
  extra stroke guarantee.
- Existing `HandAPI` has a read-only-by-default actual SDK adapter. Installed
  wujihandpy1.8/Python3.10 constructor and read/realtime signatures were checked;
  separate SDK-shaped fixture verifies mapped reads, refusal of unauthorized
  writes, SDK array layout and telemetry. No physical device commands were sent.
  USB VID/PID inventory found no matches locally or on the authorized SSH server.
 181 saved simulation samples were actually recorded and response analysis run.
  Live appended external meter records and existing injected realtime controller
  effort can be retained. A/null is not Nm/zero. No calibration data invented.

## Contact and hand-space development

Near-small35mm fails only its last nominal collision certificate. The common
estimate-only longest-prefix selector keeps the same threshold and selects34mm;
complete physical run gives29.713mm with cap contact1.0 and42um hold range.
Checking the ACTUAL compensated targets reveals thumb-pad/middle-link4 convex
hull overlap. An independent intersection LP confirms overlap at20s; this is
motor target geometry, not measured physical penetration. Nominal certification alone does not predict impedance setpoints. Final command projection from the previous legal issued
command uses no live object/force/contact inputs and records the actual sent
command in action/history. It preserves>=25um target clearance and cap contact,
but only14.557mm: not promoted. Crucially, the actual corrected physical near-small
pose path has minimum11.780mm thumb/other-digit-or-base clearance across61 samples
and original position limits pass; independent20.1s intersection LP finds no
measured-pose overlap. The finite-PD target is an impedance equilibrium under
knife reaction, not the realized configuration. Therefore14.557mm is a strict
setpoint-guard ablation, NOT a hard geometric capacity limit; the earlier inference
was retracted in the journal. Near-small is resolved for the original simulated
task and actual sampled motion. Real firmware stiffness, finite current and
contact-loss response must establish whether these preload targets transfer.
Moving middle support10mm makes index/middle interfere; moving both makes original
contact IK infeasible. Those alternative paths were rejected, not executed or
threshold-relaxed, and are not required to validate the successful measured path.

Large-high original28mm rerun barely moves(0.002mm) and loses cap contact. Saved
old records show the first error: initial actual contact at x≈−3.2mm with<0.83mm
side margin, actual front cosine≈0.449; after16s body roll increases, front cosine
falls toward0.04 and thumb4 reaches its lower position bound around17s before
contact loss. Normal torque saturation is not the cause.

Estimate-driven adaptation implemented: full pad normal/wrist contact IK, joint
travel-aware bounded inverse-static support preload, index contact tracking and
adjacent-support collision penalty, longitudinal support sites, cap-width-scaled
lateral thumb contact bias, and continuous dense-reference initialization.
Unrestricted wrist optimization violates index preload reserve; bounded wrist
still creates support interference. These geometric candidates were rejected.
Fixed-wrist full-normal35mm restores cap contact1.0 and32.408mm but body rotation
0.615rad exceeds the original0.6rad criterion. It also has a reference branch jump
requiring the original0.025rad/step limiter; classify as diagnostic, never a
certified promotion. Continuing from the previous IK pose still cannot avoid the
branch jump at23mm. A0.2×estimated cap-width lateral contact offset has a smooth,
certified nominal path and restores99.93% cap contact, but16.530mm/0.999rad body
rotation fails. This isolates the remaining support/rolling coordination problem
rather than falsely claiming success from higher normal peaks or continuous cap
contact alone. No friction/load/asset enlargement or criterion changes were used.

The full-face guard costs1.35s/command on this host, unsuitable as a30Hz hardware
loop. A reduced24-face-axis/enclosing-sphere implementation keeps every hull
vertex and positive certificates conservative; sampled checks take5.7–6.8ms,
but reject one valid narrow-margin full-face target. It is a development speed
comparison, not a verified replacement or real-device latency result.

## Frozen joint validation and limits

Actor and effective pressure/path control frozen before two NEW joint physical
runs. No retuning after outcomes. Geometry/initial-estimate bounds are synthetic
engineering sensitivity, not calibrated perception distribution.

| New condition | Task result | Evidence |
| --- | --- | --- |
|145.5×19.3×8.2mm body;32.4×7.2×2.1mm cap; proximal31.5mm;56g;1.25N constant;1frame delay +noise/bias |22.123mm, hold0.0329mm, cap99.93%, rotation0.284rad: physical task PASS |`frozen/mid-high-delay/physical-v1` |
|147.5×19.75×8.8mm body;33.6×7.8×2.4mm cap; proximal34mm;59g;0.93N variable; friction0.75/1.7 +noise |3.488mm, cap99.79%, rotation0.631rad: FAIL |`frozen/upper-geometry-friction/physical-v1` |

Variable actual passive capacity is0.940–1.042N, not a second repeated multiplier
or measured thumb force. Physical task outcomes, commanded-target constraints,
source assets, prior fitted actor, independent virtual-work verification and
hardware readings are distinct. This is local same-topology evidence, not all
140–148mm geometries or arbitrary grasps. Near-small and large are development.
Frozen upper failure confirms cap persistence alone does not solve high-end
coordination. The mid-high compensated targets also fail a strict target-only
certificate(−5.21mm lower bound), while its complete sampled measured path stays>=13.41mm clear(20.1s16.26mm).
  Thumb4 reaches the original position bound with a maximum numerical overshoot
  0.148microrad; the independent1e−7rad test flags it rather than relaxing the
  threshold. This is not evidence of real hardware limit calibration.
This is kept as firmware/preload transfer information, not a retroactive change
to the original task criterion. No new training: current limit/hand-space constraints are not
resolved by merely adding PPO updates; legacy128env warnings did not recur in
these complete single-env rollouts.

## Delivery and remaining work

Eight new continuous22s runs have original full-scene/close-up MP4 and synchronized
videos; failures and the rejected guard are included. No private photographs or
Goal HTML were published. Source and small runtime overlay reuse verified old
singlepush dependencies. One representative1.25N restored execution is recorded
in RESTORE-VERIFICATION.json. See REPRODUCE.md and HARDWARE-MEASUREMENT.md.

`extension_demo_ready=true` means retained simulation capability.
`mapping_verified=true` means array/name conversion, not true axes/zeros.
`device_interface_verified` means actual SDK imports/signatures plus fixture,
not a device connection. `real_robot_ran=false`; total axial force remains null.

Remaining real demo work: connect identified right-hand and G2 arm; obtain actual
firmware/limits/axes/zeros and authorized motion; measure separately aligned
normal/axial sustained output at identical start/middle/end grasp for>=1s, first
0.7355N then1/1.25N, recording material, rail startup/along-slot resistance,
displacement/slip and actual target/encoder timing. Calibrate only local measured
response; do not port simulated PD/gravity or assume SDK Kp. Upper dimensions still need coordinated support; near-small real deployment
needs actual firmware/preload and contact-loss response calibration rather than
assuming nominal PD targets are realized poses. This round supplies concrete implementations and
failure evidence, not a claim that every remaining issue depends on hardware.
