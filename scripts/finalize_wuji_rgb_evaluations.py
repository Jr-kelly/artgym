"""Wait for all declared trials, then audit traces and report frozen-cohort rates."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time


def write(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path,required=True)
    args=parser.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root'])
    out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    write(out/'status.json',state)
    try:
        for job in spec['jobs']:
            while True:
                prior=json.loads((root/job['run']/'status.json').read_text())
                if prior['status']=='completed':break
                assert prior['status'] not in ['failed','cancelled'],prior.get('error')
                state.update(status='waiting',waiting_for=job['run'],heartbeat=now())
                write(out/'status.json',state);time.sleep(20)
            commands=[[sys.executable,'-m','scripts.audit_wuji_rgb_policy_results',
                '--run',str(root/job['run']),'--output',str(root/job['audit'])]]
            if job.get('cohort'):
                commands.append([sys.executable,'-m',job.get('statistics_module','scripts.summarize_wuji_rgb_independent'),
                    '--audit',str(root/job['audit']),'--cohort',str(root/job['cohort']),
                    '--output',str(root/job['statistics'])])
            for index,command in enumerate(commands):
                row=dict(run=job['run'],command=command,status='running',started=now())
                state['stages'].append(row);state.update(status='auditing',heartbeat=now());write(out/'status.json',state)
                with (out/(job['name']+f'-{index}.log')).open('w') as log:
                    code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
                row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                assert code==0,row
        state.update(status='completed',finished=now())
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc));raise
    finally:write(out/'status.json',state)


if __name__=='__main__':main()
