"""Resume uploads by verifying existing names and checking the server after failures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now
from scripts.host_tool_environment import host_tool_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verification',type=Path,required=True)
    p.add_argument('--max-time',type=int,default=900);p.add_argument('--release-id',type=int,default=392488331);p.add_argument('assets',type=Path,nargs='+');args=p.parse_args()
    assert not args.verification.exists() and len({p.name for p in args.assets})==len(args.assets)
    progress=args.verification.with_suffix('.progress');progress.mkdir(exist_ok=False)
    token=subprocess.check_output(['gh','auth','token'],text=True,env=host_tool_environment()).strip()
    assert token and not any(c in token for c in '\n\r"')
    query_count=0
    def existing():
        nonlocal query_count
        query_count+=1;path=progress/f'server-query-{query_count:03d}.json'
        subprocess.run(['curl','-4','--silent','--show-error','--fail','--retry','2','--retry-all-errors',
            '--retry-delay','2','--connect-timeout','8','--max-time','30','--config','-','-o',str(path),
            f'https://api.github.com/repos/Jr-kelly/artgym/releases/{args.release_id}'],
            input='header = "Authorization: Bearer '+token+'"\n',text=True,check=True,env=host_tool_environment())
        return {a['name']:a for a in json.loads(path.read_text())['assets']}
    server=existing();records=[]
    for index,asset in enumerate(args.assets):
        assert asset.is_file();sha=hashlib.sha256(asset.read_bytes()).hexdigest();record=None
        for attempt in range(4):
            if asset.name in server:
                a=server[asset.name]
                assert a.get('state')=='uploaded' and a.get('digest')=='sha256:'+sha and a['size']==asset.stat().st_size,(asset.name,a)
                record=dict(name=asset.name,sha256=sha,asset_id=a['id'],url=a['browser_download_url'],digest_verified=True)
                break
            assert attempt<3,asset.name
            result=progress/f'upload-{index:03d}-attempt{attempt}.json'
            cmd=[sys.executable,'-m','scripts.upload_wuji_release_assets','--max-time',str(args.max_time),
                '--release-id',str(args.release_id),'--verification',str(result),str(asset)]
            with result.with_suffix('.log').open('w') as log:
                code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
            if code==0:
                one=json.loads(result.read_text());assert len(one)==1 and one[0]['sha256']==sha
                record=one[0];break
            atomic_json(progress/f'failure-{index:03d}-{attempt}.json',dict(time=now(),name=asset.name,returncode=code))
            time.sleep(2);server=existing()
        assert record is not None
        records.append(record);atomic_json(args.verification.with_suffix('.pending.json'),records)
        print(json.dumps(record),flush=True)
    args.verification.with_suffix('.pending.json').replace(args.verification)


if __name__=='__main__':main()
