# Actual continuous antirotation development results

The frozen750 policy with common initial noisy-geometry IK, bounded original
self-geometry motor projection, a lower index side contact and a full tangential
thumb motor reference completed actual tabletop pickup followed by two loaded
extend/hold/retract/hold cycles in V17. This is one nominal development example.
Necessary geometry/load generalization and real hardware remain unresolved.

The external command is40mm. The measured V17 extensions are32.21/26.44mm and
returns6.49/1.99mm. This passes the functional criterion declared before the
experiments; it does not demonstrate literal40mm measured physical travel. The
legacy0.25rad world-pose criterion remains false and is reported unchanged.
No body attachment, runtime object state reset, rail positive assistance,
collision simplification, reduced gravity or increased actuator limits is used.

| Development trial | Controller/mechanics | Resistance capacity run/start N | Extension mm | Return mm | Finding |
|---|---|---|---|---|---|
|V17|Frozen750, projected noisy nominal/lower index|.2/.2|32.21/26.44|6.49/1.99|All predeclared functional checks pass|
|V18|Same V17 actor and geometry|.5/.5|23.73/22.69|16.86/12.12|Continuous contact/holding; inadequate traction/return|
|V19|Same actor, noisy140x18x14mm estimate|.2/.2|28.94/21.47|4.17/2.75|Second extension and progressive return slip fail|
|V21|Retained750 nominal50 fit|.5/.5|24.55/23.60|18.83/15.26|No return improvement; fit stopped|
|V23|Prepared continuous wristroll plus frozen750|.5/.5|22.63/20.56|20.56/20.56|Drops first return|
|V24|Thin original full-acquisition geometry repaired, frozen750|.2/.2|25.32/21.96|5.61/6.28|No fall/contact retained; second extension fails|
|V25|Same thin path, three-geometry fitted50|.2/.2|25.81/22.27|6.73/6.50|No meaningful improvement; safely stopped at54|
|V14|Projected nominal scripted motor reference|.5/.5|24.20/20.47|20.47/20.47|Knife dropped during first return|
|V20|Scripted continuous negative6mm tangential preparation plus known wrist roll|.2/.2|31.64/22.36|2.49/~0|Improved reversal, insufficient second extension/support displacement|

Solver brake values above are passive capacities in addition to actual contact
friction, not measured real cutter resistance or a real-world upper bound.
V20 changes virtual motor travel to46mm while external rail command remains40mm;
virtual preload/position offsets do not constitute constant physical pressure.

V17 exact pair-contact fraction99.9168%; relative maximum rotation0.28625rad,
return-to-return incremental rotation0.09546rad, translation0.876mm, final
angular velocity0.00631rad/s. Videos are continuous.mp4 and hand-closeup.mp4
inside runs/antirotation-grasp-20261004/continuous/actual-table-projected-grasp-frozen750-load2-v17.
Frozen750 SHA256:11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d.

The exact direct run command is in the corresponding jobs/*/identity.json;
run its command with a fresh --output directory under the experiment clone.
Research helpers reproduce derivations in order and intentionally reject an
existing output rather than overwriting historical results. The dependency
configuration paths are included in the recoverable Git snapshot; larger
weights, traces and videos will be delivered as Release assets.

Separate forward/return motor-reference blending was rejected before physical
execution:85/405 intermediate samples failed original self geometry. The
controller was restored to the single-reference implementation. Thin130x14x10mm
geometry initially failed table clearance at pinky link4/pad; first touch/close
repair passed dense closing/transfer but full open approach still failed.
The revised repair covers all open/touch/close targets. These are geometric
preparation checks, not successful physical generalization.

Two reset-head new-mechanics training pilots closed without functional behavior
improvement; their frozen evaluations and optimizer/RNG checkpoints are retained.
The nominal50 and three-geometry54 pilots are closed negative training
fitting results. No success rate from training or development is labeled independent
validation, and no hardware result is claimed.

Isolated source/dependency recovery completed the full V17 run with identical
trace SHA. A large frozen-policy population probe reproduces training-scene
pathology before optimization; further unchanged PPO is suspended while checking
physical batch validity. This recovery/diagnosis is separate from necessary
generalization and from real hardware.
