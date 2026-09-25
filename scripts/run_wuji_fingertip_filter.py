"""Revalidate every screened geometry and publish a contact sheet and audit."""
import json
import fcntl
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

from scripts.filter_wuji_fingertip_grasps import (
    ROOT, TARGET, RULES, digest, physical_signature, check_dataset, save_json, dataset_totals,
)


def main():
    os.chdir(ROOT)
    logs=ROOT/'tmp/wuji-fingertip-filter'
    logs.mkdir(parents=True,exist_ok=True)
    lock=(logs/'filter.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    progress=dict(pid=os.getpid(),status='running',completed=[])
    for i in range(35):
        instance=f'{i:03d}'
        folder=TARGET/instance
        progress['current']=instance
        save_json(logs/'status.json',progress)
        cached=False
        if (folder/'filter_validation.json').exists():
            report=json.loads((folder/'filter_validation.json').read_text())
            cached=(report.get('physical_signature')==physical_signature()
                    and report['rules']==RULES
                    and report['screening_sha256']==digest(folder/'screening.json')
                    and report['screened_sha256']==digest(folder/'screened.npz')
                    and all(digest(folder/name)==sha for name,sha in report['outputs'].items())
                    and len(list(folder.glob('grasp-*.png')))>0)
        if not cached:
            with (logs/f'{instance}.log').open('w') as stream:
                subprocess.run([sys.executable,'-u','-m','scripts.filter_wuji_fingertip_grasps',
                                'physical','--instances',instance,'--images'],
                               stdout=stream,stderr=subprocess.STDOUT,check=True)
        report=json.loads((folder/'filter_validation.json').read_text())
        progress['completed'].append(dict(instance=instance,valid=report['valid'],train=report['train'],test=report['test']))
        print(instance,progress['completed'][-1],flush=True)
    reports=check_dataset()
    totals=dataset_totals(reports)
    save_json(TARGET/'dataset-report.json',dict(rules=RULES,instances=reports,totals=totals))
    sheet=Image.new('RGB',(7*256,5*286),'#eeeeee')
    draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(reports):
        folder=TARGET/r['instance']
        report=json.loads((folder/'filter_validation.json').read_text())
        source=report['accepted_source_indices'][0]
        frame=Image.open(folder/f'grasp-{source:03d}.png').convert('RGB').resize((256,256))
        x,y=(i%7)*256,(i//7)*286
        sheet.paste(frame,(x,y))
        draw.text((x+6,y+258),f"{r['instance']} | kept {r['valid']} | source {source}",fill='black')
    sheet.save(logs/'all-35-grasps.jpg',quality=95)
    served=ROOT/'tmp/wuji-knife-demo'
    sheet.save(served/'all-35-grasps.jpg',quality=95)
    save_json(served/'grasp-filter-report.json',dict(rules=RULES,instances=reports,totals=totals))
    progress.update(status='completed',totals=totals)
    save_json(logs/'status.json',progress)
    print('DONE',totals,flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        status=ROOT/'tmp/wuji-fingertip-filter/status.json'
        if status.exists():
            progress=json.loads(status.read_text())
            if progress.get('pid')==os.getpid():
                progress.update(status='failed',error=str(error))
                save_json(status,progress)
        raise
