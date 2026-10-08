"""One concise result table, keeping development and final initialization distinct."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/rear-sim2real-20261009';B=R/'runs/rear-sim2real-20261009'
rows=[]
for p in sorted(B.rglob('result.json')):
    r=json.loads(p.read_text());rows.append(dict(case=str(p.parent.relative_to(B)),passed=r['passed'],active_displacement_mm=r['active_displacement_mm'],body_max_rotation_rad=r['body_max_rotation_rad'],actual_joint_min_margin_rad=r['actual_joint_min_margin_rad'],first_failure_s=r['first_failure_s'],checks=r['checks'],source=str(p.relative_to(R))))
(D/'RESULTS.json').write_text(json.dumps(dict(scope='Source/model fit unchanged. Short-checks are frozen synthetic engineering sensitivities of v3. Failed v4/v5 corrections are development, not independently unseen successes. Final v6 has real postwarm history and shared SDK core. All are simulation; hardware false.',runs=rows),indent=2))
print(len(rows),'actual completed physics runs')
