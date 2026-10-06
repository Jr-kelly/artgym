# Ring-support and direct side-pinch continuation, 2026-10-06

Goal unchanged and incomplete: complete flat-table pickup→continuous>20mm active extension→generalization. Previous goal turn made progress through native support evidence and new tail lift; no success claim retained.

Eight new physical experiments (v25,v26,v27,v28,v31,v33,v34,v35) failed whole pickup. Full traces/videos and per-trial native support evaluations remain in runs/flat-table-20261006/development. Numerical geometry candidates v29/v30/v32/v36 are planning only, not physical experiments.

v25 uses actual v19 partial-lift knife pose to target ring underside support; target feasible but actual larger lift still loses grip. Stop old folded-ring timing/height branch.

New direct side pinch, complete flat tabletop start(.37,-.5695,.7541)m,yaw45°, no robot pushes and no initial overhang. Index/ thumb opposing estimated width contacts; unused digits retract. Original55g asset, gravity, torque/velocity/position clipping, table and friction retained.

v26 physically makes indexlink4/thumb contact but native normals have large downward components, no lift. v27 preloaded pad-only target still presses downward. v28 uses actual indexlink4 contact and70mrad joint reserve; fails. v31 solid-tail contact geometry has inactive folded middle blocking thumb; no useful knife contact. v33 joint wrist/hand optimization clears closed thumb self contact, but open posture collides with table/other digits. v34 adds opening plane/self constraints; leaves45um negative separation certificate, not certified clear. Physical contacts reveal middlelink4 on slider, summed normal z−270.9 of271.6 solver magnitude. v35 bounded Jacobian inward4mm virtual preload still fails; no increase to effort/friction.

v36 adds inactive-digit/knife clearance to same geometry; rejected without physics because contact error5.7mm,3 thumb self-overlap certificates and middle gap.43mm vs4mm required. v37 is one explicit top-down orientation seed using same constraints. Inspect terminal candidate and receipt before further work; it is not pickup evidence.

Important: side pinch stage runs during prefix time−24..0; old downstream pickup sequence is retained only as failed connection diagnostic. No functional transition to old grasp has been implemented for side pinch. A successful side clamp would require new actual continuous handover motor path; cannot substitute a cached perfect grip. Native whole-object evaluation and gravity/hand retention must pass first.

Useful reproduction of v34:
```bash
source runs/contact-transfer-20261006/env.sh
python -m scripts.run_wuji_flat_table --output runs/flat-table-20261006/reproduce/<fresh> \
 --resistance runs/singlepush-20261005/configs/resistance-0.73549875.json \
 --reference-control-config runs/singlepush-20261005/configs/reference-path-drive.json \
 --flat-table-prefix runs/flat-table-20261006/preparation/side-pinch-v34/prefix.json
```

No training or heldout full-flow validation; geometric planning consumes declared known pose only. No robot motion or real vision. Existing actor hash6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e unchanged. Saved behaviors remain failure evidence, not relabeled completion.

v37 terminal:contact error5.65mm,plane violation2.68mm, rejected; no physical trial. This does not prove all possible side pinches impossible. Next justified mechanism must change wrist/active digit pairing or exploit robot-created partial lift to introduce support, not repeat same pinch seed/pressure scans.
