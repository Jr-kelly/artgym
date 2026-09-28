"""Freeze all novel physical passes with an explicitly amended contact gate.

The original preregistered pool is preserved. This is a separately labelled
supplement, fixed before evaluating any learned policy on these candidates.
"""
import datetime, hashlib, json
from pathlib import Path
import numpy as np
from scripts.reference_metrics import unique_grasp_indices

R = Path(__file__).resolve().parents[1]
D = R/'research/multigrasp-20260928/data'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original = D/'fresh2805-frozen/manifest.json'
    source = D/'fresh2805-candidates.npy'
    old = json.loads(original.read_text())
    assert old['source_states_sha256'] == sha(source)
    states = np.load(source)
    eligible = [r['row'] for r in old['records'] if all(
        v for k, v in r['gates'].items() if k != 'support_contact')]
    kept = [eligible[i] for i in unique_grasp_indices(states[eligible], 20)] if eligible else []
    out = D/'fresh2805-supplement-frozen'
    out.mkdir(exist_ok=False)
    np.save(out/'base.npy', states[kept])
    manifest = dict(status='frozen', frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_states_sha256=sha(source), original_gate_manifest_sha256=sha(original),
        source_rows=kept, base_grasp_count=len(kept),
        artifact_sha256={'base.npy': sha(out/'base.npy')},
        cohort_label='new_unseen_amended_physical',
        original_preregistered_new_base_count=old['base_grasp_count'],
        selection='All posture/reach/non-old-family/alive20s/body-stable passes, deduplicated; remove only binary net-force proxy gate; no learned policy results read',
        amendment_reason='Binary tactile gate rejects known successful original records0/2; net force proxy is not necessary for physical holding. Original gate retained as primary accounting; supplement separately labelled.',
        limitation='Post-generation physical-gate amendment, not original preregistered blind cohort; geometric reach and static holding do not prove dynamic operation.',
        evidence='research/multigrasp-20260928/receipts/contact-gate-sensitivity.json')
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
