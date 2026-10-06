# Folded-finger continuation, 2026-10-06

Goal remains whole-knife full-table pickup→active slider extension>20mm→local generalization. Previous turn was progress, not completion. Preserve flat-table-v1 release as the earlier failure evidence.

New mechanism folds ring/pinky during acquisition, curls middle to avoid table. Author collision hulls clear the table at the entry target and no ring/pinky self overlap found. Ten new physical development attempts v15–v24 are preserved; current-state results are in folded-round-results.json plus each trial's flat-table-evaluation.json.

Key new behavior: v19 physically lifts knife tail/root from.754 to.805m, with hand contact and knife rotation. However the opposite blade end remains supported by table. Native table contact after12s has300 records. This is NOT complete pickup. The old extension evaluator's root-height criterion incorrectly returned continuous_pickup=true for this trajectory. Added evaluate_wuji_flat_table.py retains old result but rejects whole_pickup when native knife/table contact persists. No thresholds weakened.

v15 ring/pinky-folded approach avoids table but tips during lift. v16 delayed unfold still tips before unfolding, correcting the initial causal hypothesis. v18 preclosed middle contacts knife but pushes it inward and does not lift. v19 curled middle improves tail lift; fixed wrist then loses thumb contact and settles on table. v20 extra80mm lift loses grip. v21 slower180mm lift also loses grip. v22 combines early unfolded support and curled middle, no complete pickup. v23 explicit30Hz sim_oracle cap tracking alone does not solve grip retention. v24 declared wrist pose following also fails:1200 native table-contact records after12s, no whole pickup. All ten trials terminal.

Source interface: new oracle updates6–12s only when pickup-thumb-pose-tracking or pickup-wrist-pose-follow explicitly enabled. Pose/slider are planning estimates, not silently actor features; stage switches remain clock-based. Deployment remains unverified; real vision not implemented. A future estimate provider must replace these simulator reads. Native diagnostic table/force records remain evaluation-only.

Representative reproduction:

```bash
source runs/contact-transfer-20261006/env.sh
python -m scripts.run_wuji_flat_table --output runs/flat-table-20261006/reproduce/<fresh> \
 --resistance runs/singlepush-20261005/configs/resistance-0.73549875.json \
 --reference-control-config runs/singlepush-20261005/configs/reference-path-drive.json \
 --flat-table-prefix runs/flat-table-20261006/preparation/push-corner-v10/prefix.json \
 --postpush-pose-update --fold-outside-fingers --fold-release-start 12 \
 --middle-entry-config runs/flat-table-20261006/middle-curl-v19.json
```

v19 full panoramic/closeup MP4s each46s at30fps reside with its raw trace. Do not label root clearance as complete pickup or start frozen full-flow generalization before a real A→B success. Existing actor remains6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e.
