"""Independent quality checks after the fresh official functional-grasp pipeline.

Keep every first-stage valid candidate and its original seeded train/test split
in the reports. Apply the previously frozen posture/reach/contact requirements,
and restart all candidates for independent 20-second holding. No RL is launched
by this script, and none of the old five failed validation grasps is replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',type=int,default=2)
    parser.add_argument('--output-name',default='independent-quality')
    parser.add_argument('--generation-name',default='fresh-lowgain-functional-generation')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    assert '/' not in args.generation_name
    parent=root/'runs/wuji-goal/diagnostics'/args.generation_name
    assert '/' not in args.output_name
    output=parent/args.output_name
    output.mkdir(parents=True,exist_ok=True)
    assert not (output/'status.json').exists()
    state=dict(status='waiting_for_generation',started=now(),stages=[],scope=__doc__)
    atomic_json(output/'status.json',state)
    environment=runtime_environment(dict(project=str(root),python=sys.executable),args.gpu)

    def run(name,arguments):
        with (output/(name+'.log')).open('w') as log:
            child=subprocess.Popen([sys.executable]+arguments,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT)
        item=dict(name=name,status='running',started=now(),pid=child.pid,arguments=arguments)
        state['stages'].append(item);state['status']=name;atomic_json(output/'status.json',state)
        try:code=child.wait(timeout=1800)
        except subprocess.TimeoutExpired:child.kill();child.wait();code=124
        item.update(status='completed' if code==0 else 'failed',finished=now(),returncode=code)
        atomic_json(output/'status.json',state)
        return code

    try:
        deadline=time.monotonic()+25200
        while time.monotonic()<deadline:
            if not (parent/'status.json').exists():
                time.sleep(1)
                continue
            before=json.loads((parent/'status.json').read_text())
            if before['status']=='completed':break
            if before['status']=='failed':raise RuntimeError('Fresh candidate generation/validation failed')
            time.sleep(30)
        else:raise TimeoutError('Generation did not finish within seven hours')
        import numpy as np
        from scripts.filter_wuji_fingertip_grasps import posture_mask,ThumbReach,RULES
        dataset=before.get('dataset','knife_wuji_lowgain_fresh20260922')
        cache=root/'caches/initial_grasp/wuji'/dataset/'000'
        states=np.load(cache/'valid_grasps.npy')
        assert states.shape==(before['validation']['counts']['valid'],75) and np.isfinite(states).all()
        if len(states)==0:
            state.update(status='completed_no_valid_candidates',finished=now(),raw_candidates=1000,valid=0)
            atomic_json(output/'status.json',state);return
        if len(states)==1:train_idx=np.array([0]);test_idx=np.empty(0,dtype=int)
        else:
            order=np.random.default_rng(0).permutation(len(states))
            test_count=max(1,min(len(states)-1,int(round(len(states)*.2))))
            train_idx,test_idx=order[:-test_count],order[-test_count:]
        assert np.array_equal(states[train_idx],np.load(cache/'train/valid_grasps.npy'))
        assert np.array_equal(states[test_idx],np.load(cache/'test/valid_grasps.npy'))
        train_set=set(train_idx.tolist())
        candidate_dir=output/'candidates';candidate_dir.mkdir(exist_ok=True)
        np.save(candidate_dir/'initial_states.npy',states)
        state['status']='posture_reach';atomic_json(output/'status.json',state)
        posture=posture_mask(states);reach=ThumbReach()
        asset=root/'assets/objects'/dataset/'000'
        meta=json.loads((asset/'parameters.json').read_text())
        lower=float(ET.parse(asset/'mobility.urdf').getroot().find("joint[@name='slider']/limit").get('lower'))
        assert abs(lower-meta['joint_lower'])<1e-9
        records=[]
        for i,row in enumerate(states):
            split='train' if i in train_set else 'test'
            records.append(dict(candidate_row=i,split=split,posture_pass=bool(posture[i]),
                slider_closed=bool(abs(row[54]-lower)<.002),thumb_reach=reach.check(row,meta)))
        manifest=dict(candidate_count=len(states),source_counts=dict(train=len(train_idx),test=len(test_idx)),
            raw_candidates=1000,records=records,rules=RULES,
            slider_closed_reference=lower,
            states_sha256=hashlib.sha256((candidate_dir/'initial_states.npy').read_bytes()).hexdigest(),
            expected_object_asset_root='assets/objects/'+dataset,
            expected_object_urdf_sha256=hashlib.sha256((asset/'mobility.urdf').read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            generation_status_sha256=hashlib.sha256((parent/'status.json').read_bytes()).hexdigest(),
            scope=__doc__)
        atomic_json(candidate_dir/'manifest.json',manifest)
        code=run('static',['-m','scripts.audit_wuji_static_grasp','--hand','wuji_paper_official_actuator',
            '--task','wuji_acquisition_official_support40mrad','--object',dataset,
            '--initial-states',str(candidate_dir/'initial_states.npy'),'--output',str(candidate_dir/'static')])
        report_path=candidate_dir/'static/report.json'
        if code:
            assert code==1 and (candidate_dir/'static/trace.npz').exists()
            assert run('static_roundoff',['-m','scripts.audit_wuji_static_roundoff','--directory',str(candidate_dir)])==0
            report_path=candidate_dir/'static/offline-report.json'
        assert run('semantic_contacts',['-m','scripts.audit_wuji_settled_contacts','--object',dataset,
            '--candidates',str(candidate_dir),'--output',str(output/'semantic-contacts')])==0
        static=json.loads(report_path.read_text())
        contacts=json.loads((output/'semantic-contacts/report.json').read_text())
        assert static['initial_state_sha256']==contacts['initial_states_sha256']==manifest['states_sha256']
        for row in records:
            i=row['candidate_row']
            row.update(stable20s=static['records'][i]['stable20s'],
                contact_pass=contacts['records'][i]['passed_existing_contact_rule'])
            row['all_gates_pass']=bool(row['posture_pass'] and row['slider_closed'] and row['thumb_reach']['passed']
                and row['stable20s'] and row['contact_pass'])
        counts={split:dict(first_stage_valid=sum(r['split']==split for r in records),
                          accepted=sum(r['split']==split and r['all_gates_pass'] for r in records))
                for split in ['train','test']}
        exact_overlap={row.tobytes() for row in states[train_idx]} & {row.tobytes() for row in states[test_idx]}
        result=dict(status='completed',raw_candidates=1000,counts=counts,records=records,
            static_report=str(report_path.relative_to(root)),initial_states_sha256=manifest['states_sha256'],
            exact_duplicate_rows_across_splits=len(exact_overlap),
            scope=__doc__)
        atomic_json(output/'report.json',result)
        state.update(status='completed',finished=now(),raw_candidates=1000,counts=counts)
        atomic_json(output/'status.json',state)
    except Exception as exc:
        state.update(status='failed',finished=now(),error=repr(exc));atomic_json(output/'status.json',state);raise


if __name__=='__main__':main()
