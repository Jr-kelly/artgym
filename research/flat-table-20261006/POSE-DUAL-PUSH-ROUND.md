# Pose-conditioned two-pad push round

Goal remains incomplete. Seven new full physical episodes v68/v69/v70/v71/v72/v74/v75, two planning stages v67/v73. Whole flat start(.37,-.5695,.7541)m,yaw45deg; unchanged table, original gravity/friction/resistance/finitePD/actuator limits, retained actor. No physical-state writes after initialization. Development diagnostics only; no frozen/full-flow generalization.

New mechanisms: bent two-pad native material-point pose tracking; virtual-work side-force motor targets; actual composed actuator gain injection; unequal lever-arm moment allocation; tilted real side-center approach; actual-pose wrist following. Pose source explicit sim_oracle30Hz during3–7s push plus one postpush update. B still uses same physical state and history, but no whole pickup has been acquired.

v68 position following unloads contact. v69 wrong actuator/reaction sign; v70 sign fixed but generic100Nm/rad instead of actual.18–.456Nm/rad. These are erroneous-config diagnostics, not force-capacity experiments. v71 fixes both, moves56.93mm,yaw3.75deg. v72 moment allocation moves72.69mm,yaw−.34deg, unintended−10mm slider stop. v74 geometry has0.5mm table clearance; actual downnormal mean−.475N/contact disproves reduced-downforce hypothesis, moves44.95mm,yaw22.12deg. v75 wrist following holds44.24deg but moves2.92mm; acquisition fails, accidental slider+25.60mm. Active operation displacement0. Accidental slider motion excluded.

Stop same-wrist double-pad tracking/force/moment/tilt variants. Next needs changed native contact/support topology or useful targeted learning from real flat-table trajectories. Do not restart failed auxiliaryPPO or run pressure/gain/timing scans.

Eight full46s MP4 cover v71/v72/v74/v75, wide+close. Source snapshot and reproduce-command.json reproduce current v75 FAILURE: source runs/contact-transfer-20261006/env.sh and change --output fresh. Final source snapshot is not exact for historical intermediate v68–v72 versions; errors/traces authoritative. v74 extra-source snapshot separately retained. No real vision/hardware. Normal solver contributions only; total axial force missing; virtual-work target is not measured constant force.

Local short-window useful occupancy only, not4h compliance. Four remoteH200 verified idle, no filler or failed auxiliary restart. Original monitor3068820 preserved; this round monitor stopped, all owned jobs terminal. Private attachment/media not published.
