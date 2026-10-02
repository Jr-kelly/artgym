"""Paired slot registration. Metadata never enters the policy observation."""
import hashlib
import json

ROUND = 'width-student-distillation-20261002'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def slots(arm):
    if arm not in ('C', 'G'):
        raise ValueError('Arm must be C or G')
    rows = []
    for group, counts in enumerate([(32, 32, 32, 32), (22, 21, 0, 21), (22, 21, 0, 21)]):
        instance = group if arm == 'G' else 0
        for source, count in enumerate(counts):
            for _ in range(count):
                rows.append(dict(slot=len(rows), group=group, source=source, instance=instance,
                                 geometry=['baseline', 'W110', 'W120'][instance]))
    assert len(rows) == 256
    return rows


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def real_size_slots(arm):
    assert arm in ('C','G')
    rows=[]
    for source in range(4):
        for _ in range(16):
            rows.append(dict(slot=len(rows),group=0,source=source,instance=0,geometry='baseline'))
    for _ in range(192):
        rows.append(dict(slot=len(rows),group=1,source=3,instance=1 if arm=='G' else 0,geometry='real' if arm=='G' else 'baseline'))
    return rows
