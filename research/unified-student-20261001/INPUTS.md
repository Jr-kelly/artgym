# Initial-calibration-conditional student interface

| Field | Dimension | Units / frame / time | Normalization | Source in code | Required deployment source |
|---|---:|---|---|---|---|
| Initial q |20|rad at reset|joint limits → [-1,1]|ArtManip._get_init_obs|joint encoders at initialization|
| Initial knife base + link1 poses |14|m, xyzw, hand base; initial only|fixed teacher public statistics; quaternion frame Rx(-90°), fixed hemisphere|wuji_knife_frame + wuji_quaternion_hemisphere|external initial pose calibration; not established on hardware|
| Initial fingertip origins |15|m, hand base, initial|fixed teacher public statistics|cached URDF FK|FK(initial q)|
| Initial two bounding boxes |6|m, canonical acquisition axes|fixed teacher public statistics|fixed asset extents, y/z swapped|known fixed object geometry|
| Current q |20|rad at observation|joint limits → [-1,1], then fixed actor statistics|_get_hand_proprio_obs|joint encoders|
| Previous policy action |20|dimensionless, last executed action|fixed actor statistics|actions buffer|controller memory, distinct from targets|
| External slider command |1|m relative to initialized slider|fixed actor statistics|goal_obj_dof_pos-init_obj_dof_pos|external command generator|
| Current fingertip origins |15|m, hand base|fixed actor statistics|student path WujiTorchForwardKinematics(q), replaces rigidbody truth|URDF FK of measured q|
| Teacher current poses + physics + slider state |21|pose14, mass2, friction1, damping1, stiffness1, slider displacement1, velocity1; total21|frozen teacher slice111:132|teacher_privileged_obs_buf|training supervision only; never deployment|
| Critic contact auxiliary |5|binary current contact|frozen shared statistics|raw132:137|zeroed along with teacher fields before student player; no contact sensor assumed|
| Student temporal input |2055|50×(normalized q20+previous action20) + transformed initial55|q limit scaling; initial raw canonical coordinates; no adaptive stats|student interface install_legal_public|same available inputs above|
| Actor RNN |4×512 state (actor h/c, critic h/c)|pre-action; reset per environment|fixed layer normalization|player.states|local memory; privileged dummy fields enforced for critic too|
| Action output |20|dimensionless clipped[-1,1]|teacher unchanged|frozen actor|original controller|
| Joint target |20|rad|joint limit clamp; nonthumb init target+.04a; thumb previous target+.025a|WujiAcquisition.actions_to_targets; preflight verifies actual target|controller can maintain issued targets; S0 does not consume targets|

Whole-policy execution uses a single student encoder and teacher actor, with no source ID, teacher latent mixing at evaluation, or failure-triggered expert takeover. Initial calibration is a condition, not a verified real sensor capability. Source strata are sampler metadata only. Student public FK must be paired with teacher original public observations before interpreting closed-loop differences.

The student observation uses the same transformed initial55 convention as the actor. This deliberately corrects the legacy generic student method, which returned the untransformed initial observation. C1 output is constant during a rollout because these55 values are constant; C0 is one global vector. S0 reuses repository temporal layers (192 channels,5 causal layers,kernel3,dilation2; receptive field63, history50). Dropout is disabled in both supervision and behavior to keep modes identical. Only encoder parameters are optimized.

SC controlled repair adds21 dynamic known-command fields after the2055 S0 input: normalized issued joint targets20 and external slider command/.04. Target memory initializes from issued reset commands and follows the original .04 support/.025 thumb recurrence with the same limit/scale round trip. It never reads simulator targets into policy inputs. The initial encoder branch consequently accepts55 static +21 dynamic fields; these76 must not all be described as initial calibration. The masked control has identical architecture and zeroes all21 additional fields.
