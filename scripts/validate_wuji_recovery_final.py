"""CPU-only enforcement of the frozen final batch contract before simulation."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_final_batch(root, states, models, protocols, final_phase, static=False):
    root = Path(root)
    report = root / 'research/artmanip-recovery-20260930'
    manifest = json.loads((report / 'data/manifest.json').read_text())
    final = next(x for x in manifest['entries'] if x['split'] == 'final' and x['source'] == 'all')
    states_sha = sha(root / states)
    is_final = states_sha == final['sha256']
    if not is_final and not final_phase:
        return None
    assert is_final and final_phase, 'Final cohort requires the reserved frozen evaluation phase'
    assert not static, 'Static diagnostics are not part of the final frozen batch'
    frozen = json.loads((report / 'final-freeze.json').read_text())
    assert frozen['final_states']['sha256'] == states_sha
    assert len(models) == len(dict(models)), 'Duplicate model names'
    assert protocols and len(protocols) == len(set(protocols))
    assert set(protocols) <= set(frozen['protocols'])
    for name, path in models:
        expected = frozen['models'][name]
        assert path == expected['path'] and sha(root / path) == expected['sha256'], 'Frozen weight mismatch'
    requested = {(name, protocol) for name, _ in models for protocol in protocols}
    for path in (root / 'runs/artmanip-recovery-20260930').glob('*/plan.json'):
        plan = json.loads(path.read_text())
        if plan['states_sha256'] == states_sha:
            prior = {(name, protocol) for name in plan['models'] for protocol in plan['protocols']}
            assert not requested & prior, 'Final cells already attempted; preserve evidence and audit infrastructure failures before any retry'
    return sha(report / 'final-freeze.json')
