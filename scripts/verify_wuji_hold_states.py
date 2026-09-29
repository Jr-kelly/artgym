"""Reproduce frozen perturbations without overwriting any evaluation data."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=ROOT/'research/hold-20260929/data/manifest.json'
    entries=json.loads(manifest.read_text())['entries']
    candidates=ROOT/'research/multigrasp-20260928/data/candidates.npy'
    source=np.load(candidates);hand=WujiKinematics()
    hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    checked=[]
    for item in entries:
        path=ROOT/item['path'];saved=np.load(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        generated=states_for_seed(source[item['row']:item['row']+1],item['seed'],hand,trials=item['n'])
        assert np.array_equal(saved,generated),item['path']
        checked.append(dict(**item,bitwise_reproduced=True))
    for row in [0,1,2,3,11]:
        own=[x for x in entries if x['row']==row]
        assert len({x['seed'] for x in own})==2
    collisions=[dict(left=x['path'],right=y['path'],seed=x['seed']) for i,x in enumerate(entries)
                for y in entries[:i] if x['seed']==y['seed']]
    result=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='passed',entries=checked,
        source_sha256=hashlib.sha256(candidates.read_bytes()).hexdigest(),cross_source_seed_collisions=collisions,
        scope='All stored data bitwise reproduced from frozen seeds; within each source dev/final distinct. A cross-source seed collision shares noise draws across different base grasps, not identical states; do not claim all random draws globally independent.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],files=len(checked),collisions=collisions)))


if __name__=='__main__':main()
