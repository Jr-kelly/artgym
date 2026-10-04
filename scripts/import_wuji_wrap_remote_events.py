"""Mirror fetched worker job provenance into the required parent journal."""
import hashlib,json
from scripts.record_wuji_wrap_goal import D,record


def main():
    marker=D/'IMPORTED-REMOTE-EVENTS.json'
    imported=set(json.loads(marker.read_text()) if marker.exists() else [])
    count=0
    for line in (D/'events-remote.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row['utc']<'2026-10-04T10:51:40':continue
        key=hashlib.sha256(line.encode()).hexdigest()
        if key in imported:continue
        job=row['job'];cmd=job['command']
        name=cmd[cmd.index('--output')+1].rstrip('/').split('/')[-1]
        identity=dict(name=name,machine=job['machine'],pid=job.get('pid'),
                      start_utc=job.get('start_utc'),gpu=job['gpu'])
        details=dict(evidence='research/wrap-force-20261004/events-remote.jsonl',
                     remote_event=row,remote_event_sha256=key,
                     next='Continue current finite comparison/delivery; original remote timestamps preserved')
        details['active_job' if row['event']=='remote_job_started' else 'closed_job']=identity
        record('fetched_'+row['event'],**details);imported.add(key);count+=1
    marker.write_text(json.dumps(sorted(imported),indent=2)+'\n');print(count)


if __name__=='__main__':main()
