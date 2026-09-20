# Wuji utility-knife reference

See [the reproduction guide](../../../wuji_demo.md) for the video, installation,
commands, measured results and the scope of this scripted simulation.

The default uses `fingertip_preset.yaml` and `slim/mobility.urdf`: a 147 × 19 × 11 mm
closed envelope, 35 g total mass, 8 mm handle and 3 mm raised slider. The 9 mm blade
is visual only. The recorded initial state comes from validated anchor grasp 52,
with fingertip support and the blade toward the thumb/index side. The preset
contains all 49 full-joint waypoints at their original numeric precision.

Only the hand is commanded. The handle is free, the slider drive stiffness is zero,
and the default is one 12-second cycle. Knife surface friction is 3 and passive
slider damping is 0.3. Cross-finger/distal-to-palm self-collision is enabled.
No latch or cutting interaction is simulated. Geometry assumptions and the source
knife hash are in `slim/parameters.json`; playback checks both URDF hashes.

`slim_preset.yaml` preserves a superseded slim preview with the blade toward the
little-finger side. `preset.yaml` and `grasp_seeds.yaml` belong to the historical
thicker knife. They are not the default and should not be mixed with the new asset.
The default preview can run without the original research grasp caches.
