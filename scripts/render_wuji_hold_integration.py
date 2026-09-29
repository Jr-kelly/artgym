"""Render four predeclared source trials from final singleton/shared policies."""
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from scripts.record_wuji_hold_event import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    deadline=datetime.datetime(2026,9,29,16,30,tzinfo=datetime.timezone.utc).timestamp()
    while time.time()<deadline:
        path=ROOT/'research/hold-20260929/receipts/backup-integration.json'
        entries=json.loads(path.read_text())['entries'] if path.exists() else []
        final=[entry for entry in entries if entry['epoch']==3000]
        if len(final)==2:break
        time.sleep(30)
    else:raise TimeoutError('Integration video checkpoint deadline')
    while time.time()<deadline:
        processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True)
        if not [line for line in processes.splitlines() if line.strip() and 'ToDesk' not in line]:break
        time.sleep(30)
    else:raise TimeoutError('Local video GPU occupied by another task')
    results=[]
    for condition in ['singleton','shared']:
        entry=next(x for x in final if x['name']==f'hold_integrate_{condition}_seed2903')
        cp=ROOT/entry['path'];assert hashlib.sha256(cp.read_bytes()).hexdigest()==entry['sha256']
        name=f'video-integration-{condition}-fixed5'
        record('integration_video_started',name+': four fixed source trial0 rows, local4090 separate render',
            ['research/hold-20260929/integration-video-plan.json'],'Render actual final policy; retain every source outcome')
        subprocess.run([sys.executable,'-m','scripts.run_wuji_hold_job','--name',name,'--gpu','0','--timeout','900','--','PYTHON',
            '-m','scripts.render_wuji_multigrasp','--checkpoint',str(cp),'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_bridge3_20260922','--initial-states','research/hold-20260929/data/integration-final.npy',
            '--initial-state-rows','0','128','256','384','--video','--output',f'runs/hold-20260929/{name}/evidence',
            '--stage-seconds','5','--span','.04','--seed','2026092930'],cwd=ROOT,check=True)
        path=ROOT/f'runs/hold-20260929/{name}/evidence/report.json';report=json.loads(path.read_text())
        results.append(dict(condition=condition,report=str(path.relative_to(ROOT)),strict=report['stable_full_all_endpoints'],
            by_source={source:report['records'][i]['stable_full_all_endpoints'] for i,source in enumerate([0,1,2,3])}))
        record('integration_video_completed',name+': strict '+str(report['stable_full_all_endpoints'])+'/4; individual source outcomes recorded',
            [str(path.relative_to(ROOT))],'Inspect frames and archive videos/raw traces; do not replace frozen512 metrics')
    (ROOT/'research/hold-20260929/video/integration-render-results.json').write_text(json.dumps(dict(status='completed',results=results),indent=2)+'\n')


if __name__=='__main__':main()
