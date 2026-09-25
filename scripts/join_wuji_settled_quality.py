"""Join independent settled-candidate checks without changing source splits."""
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    path=root/'runs/wuji-goal/diagnostics/lowgain-settled-grasps-v1'
    files=[path/'candidates/manifest.json',path/'candidates/static/report.json',
           path/'semantic-contacts/report.json',path/'status.json',path/'semantic-contacts/status.json']
    manifest,static,contacts,status,contact_status=[json.loads(f.read_text()) for f in files]
    assert status['status']==contact_status['status']=='completed'
    assert manifest['states_sha256']==contacts['initial_states_sha256']
    assert manifest['states_sha256']==static['initial_state_sha256']
    records=[]
    for source in manifest['records']:
        row=dict(source)
        row.update(static_stable20s=False,semantic_five_contact_pass=False,all_gates_pass=False)
        if row['restarted']:
            i=row['candidate_row']
            assert contacts['records'][i]['candidate_row']==i
            row['static_stable20s']=static['records'][i]['stable20s']
            row['semantic_five_contact_pass']=contacts['records'][i]['passed_existing_contact_rule']
            row['all_gates_pass']=bool(row['posture_pass'] and row['slider_closed'] and row['thumb_reach']['passed']
                and row['static_stable20s'] and row['semantic_five_contact_pass'])
        records.append(row)
    counts={split:dict(source=sum(r['split']==split for r in records),
                       accepted=sum(r['split']==split and r['all_gates_pass'] for r in records))
            for split in ['train','test']}
    result=dict(status='completed',counts=counts,records=records,
        initial_states_sha256=manifest['states_sha256'],
        scope='New settled states checked by separate GPU static20s and CPU semantic-contact2s runs. Static feasibility, not learned actuation or held-out manipulation success. Original33/5 denominators preserved.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (path/'joined-quality-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(counts))


if __name__=='__main__':main()
