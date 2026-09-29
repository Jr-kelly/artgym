"""Build a portable checkpoint index from verified backups and immutable releases."""
import argparse
import datetime
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--published',action='store_true',help='Use only after confirming the GitHub release is published')
    args=parser.parse_args()
    research=ROOT/'research/hold-20260929';receipts=research/'receipts';assets={}
    for path in receipts.glob('release-*.json'):
        try:items=json.loads(path.read_text())
        except json.JSONDecodeError:continue
        if not isinstance(items,list):continue
        for item in items:
            if isinstance(item,dict) and item.get('digest_verified'):assets[item['name']]=item
    entries=[]
    for path in sorted(receipts.glob('backup-*.json')):
        for item in json.loads(path.read_text()).get('entries',[]):
            name=item['name'];asset=assets.get('wuji-'+name+'.tar.gz')
            role='core matched continuation'
            if 'seed2902' in name:role='independent continuation RNG replication; same parent and test cohort'
            if 'integrate_' in name:role='shared pool continuation' if 'shared' in name else 'singleton consolidation control'
            entries.append(dict(**item,role=role,archive=asset,
                release_url='https://github.com/Jr-kelly/artgym/releases/download/wuji-hold-20260929-v1/'+asset['name'] if asset else None,
                release_status='published' if args.published else 'draft until final delivery; URL resolves only after publication',
                restore='python -m scripts.restore_wuji_hold_run ARCHIVE.tar.gz'))
    parents=json.loads((receipts/'parent-weights.json').read_text())
    result=dict(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parents=parents,
        checkpoints=entries,verified_asset_count=len(assets),assets=list(assets.values()),
        scope='Every scheduled checkpoint retained; complete archives additionally contain all trainer nn weights, optimizer state, TensorBoard and logs. Parent release and historical successes preserved. Core final CP2000 primary, development selected CP1500 source3 dense only supplementary; integration final CP3000 predeclared.')
    (research/'weights-index.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(entries),'verified scheduled checkpoints;',len(assets),'verified release assets')


if __name__=='__main__':main()
