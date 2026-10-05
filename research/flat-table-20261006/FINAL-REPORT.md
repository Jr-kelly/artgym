# G2/Wuji full-table pickup progress, 2026-10-06

**The requested continuous full-table pickup→extension is not achieved.** Fourteen development physical attempts preserve the existing push actor. New behavior: a real two-pad push moves a fully supported knife about71mm; a fixed-world-X continuation reaches about78.5mm while keeping the knife flat on the table. Safe withdrawal avoids the initial branch jump. A declared postpush pose update regenerates arm acquisition and transfer targets in the same physical episode. The subsequent functional grasp fails at table/finger entry; no new>20mm active extension or pickup success.

Full-table start is root(0.370,-0.5695,0.7541)m,yaw45°, nominal144×19×8mm body, slider-up. Table remains x[.3,.9],y[-.63,.17],z.75. Initial footprint is fully supported; edge overhang is produced by robot contact. Original finite PD, URDF limits,55g mass, gravity and contact retained. Nominal reference brake0.73549875N, hand friction.8, knife friction1.8 are engineering settings. No physics state writes between stages; switching uses clock and one explicit oracle observation. Operation scoring starts at clock16s after24s physical prefix; unintended slider motion is excluded from active score.

| Development case | Actual postpush movement | Result and mechanism |
|---|---:|---|
| push-v5 |70.8mm|Flat side translation and safe withdrawal; yaw45→−1.96°, fixed old grasp misses|
| pose-v5 |70.8mm|Pose-regenerated arm IK errors<1µm; open ring/pinky encounter table, knife tips upright during lift|
| corner-v10 |78.5mm|Rootx.3019,yaw−7.21°; support retained, functional finger entry still fails|
| corner-v13 |167mm including fall|AdditionalX push loses support before pickup; reject|
| side-v8/v9 |≈0mm|Side-normal topology makes no useful knife contact; stop|
| balanced-v12 |69mm|Measured finger-deflection compensation reverses yaw to68.5°; functional IK rejected|
| balanced-v14 |73.4mm|Intermediate compensation yieldsyaw.58°; still table entry failure|
| yaw90-v11 |36mm|Entire initial footprint supported; finalyaw105°, functional path cannot be reached|

Other early failures and every saved trace are in results.json. All are development, **no frozen validation**. No placement or geometry/load generalization claim because A→B never connected. The retained old edge-start1.25N24.366mm remains independently validated historical baseline; it was not rerun or renamed a new full-table result.

Four useful auxiliary PPO pilots used retained edge-start episodes, loads.7355/1/1.25N and observation/placement perturbations; they are explicitly not new flat-table training.67/66/68/66 updates ended with safe checkpoint saves. No complete behavior in more than2400 sampled episodes; postpickup body stability dominates. These candidates are not promoted. Runtime library/profile failures are logged. No indefinite extension of unproductive training.

Resource monitor final observed window910.8s, whole remote machine mean47.87%; not a four-hour compliance claim. Local single-scene graphics/physics did not sustain40%; see measured status. All owned compute is stopped after delivery; checkpoint records preserve resume entry. Protected pre-existing processes untouched.

Pose source sim_oracle only; one postpush update after withdrawal. Position bias and explicit JSON observation interface remain for future simulated estimation/real vision. No real camera or robot motion occurred. Current deployment remains limited by functional pickup/table clearance plus live localization and hardware response measurements. Axial total contact force remains missing.

Next justified mechanism: choose a grasp that folds ring/pinky outside the edge and first lifts with index/middle/thumb, then actually transfers to the proven operation support. Existing full-wrap low approach cannot be adapted merely by changing arm IK. Do not repeat pad-height/overpush scans or continue auxiliary held-edge PPO without a changed hand-contact mechanism.

See REPRODUCE.md and report.html for continuous all-stage videos. A failed concrete alternative is delivered under the attachment's structural-obstacle provision; the goal remains unresolved.
