# Wuji utility-knife reference

This is a generated, scripted contact-manipulation example, not a pretrained
ArtManip policy. See [the Wuji guide](../../../wuji.md) for results and commands.

The default preview now uses `fingertip_preset.yaml` and `slim/mobility.urdf`: a
147 x 19 x 11 mm closed envelope, 35 g total mass, 8 mm handle and 3 mm raised
slider, following the sourced NT A-300GR reference. The 9 mm blade is visual
only. It starts from validated paper anchor grasp 52, with fingertip support
and the blade pointing toward the thumb/index side. Palm contact is not required.
Full joint waypoints preserve the recorded commands, including numeric precision.
The default is one 12-second cycle.
Only the hand is commanded. Preview friction is 3 and passive slider damping
is 0.3; this is not the paper training environment's damping of 1000, and no
automatic latch is simulated. Cross-finger/distal-to-palm self-collision is on.
The geometry/mass assumptions and original paper-asset hash are in
`slim/parameters.json`. Playback verifies the hand and knife URDF hashes.
The rendered single-environment check reaches 35.68 mm and returns to zero,
with 1.54 mm maximum handle drift. No sampled palm contact occurred; the ring
fingertip occasionally loses contact, so this is not a claim of uninterrupted
five-finger contact. The preview gate additionally checks four-fingertip contact
fractions and blade direction. This is not a substitute for learned-policy
evaluation or a test of holding the knife against cutting forces.

`slim_preset.yaml` retains the superseded slim preview with the blade toward the
little-finger side; it is no longer the default or the served video.

`preset.yaml` and the seeds described below are the **historical thick model**.
It is available explicitly with `--preset assets/demo/wuji_knife/preset.yaml`;
its grasp/motion must not be applied to the slim object.

`preset.yaml` contains the hand-asset checksum, DOF order, initial free-object
pose (in the hand-base frame; quaternion XYZW), joint state/targets, and 121 thumb
waypoints. The other 16 joints retain their grasp targets. Time is in seconds,
joint angles in radians, and dimensions in metres. Only the hand receives
commands during playback; the slider has zero position-drive stiffness.

`grasp_seeds.yaml` contains seven local candidate seeds. The training preparation
script perturbs three thumb joints and runs the original ArtGrasp validator.
Seeds are not labelled as valid grasps; validation generates the actual caches.

The reference was produced with `build_wuji_knife_demo`,
`search_wuji_knife_side_grasp`, `run_wuji_knife_demo`,
`plan_wuji_knife_motion`, and `refine_wuji_knife_grasp`. The checked-in reference
lets the demo run without repeating that search. Changing the hand URDF or knife
dimensions requires a new search and physical validation.

The hand uses the imported ArtBot masses, limits and gains, with approximate
convex collision shapes and self-collision disabled as in the source USD. The
knife uses two collision boxes, a visual blade, and a passive prismatic joint;
there is no latch, cutting interaction, or hardware backend.
