"""Reconcile durable G2 trial events with actual local processes and artifacts."""
from datetime import datetime,timezone
import argparse
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,default=ROOT/'runs/g2-tabletop-v1');args=parser.parse_args()
    run=args.run_root.resolve();journal=run/'events.jsonl'
    prior=[json.loads(l) for l in journal.read_text().splitlines() if l.strip()] if journal.exists() else []
    finished={r['name'] for r in prior if r.get('event')=='trial_finished'};current=[]
    for file in sorted(run.glob('*-process.json')):
        p=json.loads(file.read_text());name=file.name[:-len('-process.json')];proc=Path('/proc',str(p['pid']),'stat')
        alive=proc.exists() and proc.read_text().split(') ')[1][0]!='Z'
        result=run/name/'report.json';failure=run/name/'failure.json'
        status='running' if alive else 'complete' if result.exists() else 'failed_or_preflight_rejected'
        row=dict(name=name,pid=p['pid'],status=status)
        if result.exists():
            r=json.loads(result.read_text());row.update(grasp_success=r.get('grasp_success'),whole_success=r.get('whole_success'),failure_class=r.get('failure_class'))
        if failure.exists():row['exception']=json.loads(failure.read_text())
        current.append(row)
        if not alive and name not in finished:
            artifact=result if result.exists() else failure if failure.exists() else run/(name+'.log')
            event=dict(event='trial_finished',observed_at=datetime.now(timezone.utc).isoformat(),artifact=str(artifact),
                artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.exists() else None,
                exit_code='unavailable: detached original launcher',**row)
            with journal.open('a') as stream:stream.write(json.dumps(event)+'\n')
    snapshot=dict(observed_at=datetime.now(timezone.utc).isoformat(),trials=current)
    (run/'current-status.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    print(json.dumps(dict(running=[r for r in current if r['status']=='running'],total=len(current))))


if __name__=='__main__':main()
