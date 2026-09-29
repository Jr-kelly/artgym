"""Render predeclared historical trial zero after all final checkpoints verify."""
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
        path=ROOT/'research/hold-20260929/receipts/backup-core.json'
        entries=json.loads(path.read_text())['entries'] if path.exists() else []
        final=[entry for entry in entries if entry['epoch']==2000]
        if len(final)==4:break
        time.sleep(30)
    else:raise TimeoutError('Final checkpoint video wait deadline')
    # This renderer is intentionally local GPU0. Do not compete with another
    # compute task; an existing desktop session alone is permitted.
    while time.time()<deadline:
        processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True)
        others=[line for line in processes.splitlines() if line.strip() and 'ToDesk' not in line]
        if not others:break
        time.sleep(30)
    else:raise TimeoutError('Local render GPU occupied by another compute task')
    outputs=[]
    for row in [3,11]:
        for condition in ['original','dense1']:
            name=f'video-final-r{row}-{condition}-fixed5'
            entry=next(x for x in final if x['name']==f'hold_r{row}_{condition}_seed2901')
            cp=ROOT/entry['path'];assert hashlib.sha256(cp.read_bytes()).hexdigest()==entry['sha256']
            record('final_representative_video_started',f'{name}: fixed historical trial0; separate local4090 evaluation, not frozen128 quantitative evidence',
                ['research/hold-20260929/video/plan.json','research/hold-20260929/receipts/backup-core.json'],
                'Render actual learned policy and retain true outcome')
            command=[sys.executable,'-m','scripts.run_wuji_hold_job','--name',name,'--gpu','0','--timeout','900','--','PYTHON',
                '-m','scripts.render_wuji_multigrasp','--checkpoint',str(cp),'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator',
                '--object','knife_wuji_bridge3_20260922','--initial-states',f'research/hold-20260929/video/historical-row{row}-states.npy',
                '--initial-state-rows','0','--video','--output',f'runs/hold-20260929/{name}/evidence',
                '--stage-seconds','5','--span','.04','--seed','2026092820']
            subprocess.run(command,cwd=ROOT,check=True)
            report=ROOT/f'runs/hold-20260929/{name}/evidence/report.json'
            result=json.loads(report.read_text());outputs.append(dict(source=row,condition=condition,report=str(report.relative_to(ROOT)),
                strict=result['stable_full_all_endpoints'],alive=result['alive_full'],checkpoint_sha256=entry['sha256']))
            record('final_representative_video_completed',name+': actual strict '+str(result['stable_full_all_endpoints'])+'/1',
                [str(report.relative_to(ROOT))],'Inspect fixed frame contact sheets, archive raw trace and video')
    out=ROOT/'research/hold-20260929/video/final-render-results.json'
    out.write_text(json.dumps(dict(status='completed',results=outputs),indent=2)+'\n')


if __name__=='__main__':main()
