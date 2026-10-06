# Partial-lift regrasp round, 2026-10-06

Goal remains incomplete. Thirteen full new physical episodes plus the centered-pusher prefix failure and stopped schedule-error run are development evidence. Whole flat-table pickup and continuous extension both false; no frozen/full-flow generalization performed.

New mechanisms: middle/thumb direct pinch; solid-body proximal clearance; broad palm with actual G2/placement constraints; wrist/index/thumb partial-lift regrasp; three-contact support retention; explicit30Hz sim_oracle pose consumer; once postregrasp pose update; intermediate contact preserving trajectory; actual rail contact; loaded motor offset retention; native index material-point preservation. All physical episodes begin with whole144x19x8mm knife flat at(.37,-.5695,.7541),45deg, original fixed table; state setters occur only at initialization.

Middle/thumb v41 fails from actual middlelink3 pressing slider downward. Proximal clearance defeats its contact geometry. Broad palm hand geometry is reachable only without G2 constraints; actual G2/placement candidates do not establish contact and were not simulated. v50+ wrist regrasp releases index/middle before thumb clamp, knife returns to table or drops. The authored compound body has solid cap at z−58mm, while several early top clamps incorrectly targeted empty center at z+54mm. True rail target fixes material existence but actual support still releases at motor switch. Fixed-wrist real-rail thumb residual9.8–24mm rejects further physics.

All videos full46s, simultaneous wide/close render streams, no stitched fragments. Success gates use actual native table records and held pickup, not root height alone. Old actor and original force/velocity/position limits, gravity, friction and resistance retained. Pose sources are declared simulation oracle and diagnostic prior trajectories; no real vision/hardware claim. Native axial total force remains missing.

Auxiliary three original-operation PPO jobs finished200additional updates each (100→300),12new checkpoints retained,0whole36s training success; no model promotion. Remote resource mean47.7343% across2084.96s, not four-hour compliance. No filler computation or subagents.

Reproduce native-point-v63 by reading reproduce-command.json, replacing --output with a fresh directory, sourcing runs/contact-transfer-20261006/env.sh, and executing its exact python command. Source/asset/actor hashes are in the trial source-hashes.json; reports/traces in runs/flat-table-20261006/development, planning evidence separately under preparation. This entry reproduces failure, not successfulA→B.

Next: maintain actual loaded index support BEFORE first wrist movement, then establish thumb contact on real material while support remains. Current soft-extreme/native-point path and fixed wrist branches stopped; do not repeat their timing/seed/preload variants. Goal remains active; no external vision blocker.
