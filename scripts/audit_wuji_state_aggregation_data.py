"""Check fixed collection, split identities, weights and actual optimizer budgets."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.audit_distillation_runtime import tensor_digest
from scripts.analyze_wuji_state_encoder_evaluations import analyze


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1];folder=args.folder
    state=json.loads((folder/'status.json').read_text());spec=state['spec']
    initial=root/spec['initial'];artifact=torch.load(initial,map_location='cpu')
    initial_tensor=tensor_digest(artifact['state_encoder'])
    result=dict(scope='Development-only fixed collection and optimizer audit; not independent task success.',
        initial_sha256=digest(initial),collections=[],fits=[],wording_clarifications=[
        'The30 heldout validation rows are excluded from gradients; physical development evaluation includes fitting rows.',
        'Pinned preflight status heartbeat updates_completed remains1 after2 optimizer steps. Checkpoint update,Adam counters and sample totals verify2. Formal1000 count is correct. Main source terminal counter corrected; running immutable source retained.'])
    for seconds in [2,5]:
        runtime=analyze(folder/f'runtime-{seconds}s');assert runtime['actual_transitions']==1800
        path=folder/f'student-data-{seconds}s'
        metrics=analyze(path)
        report=json.loads((path/'report.json').read_text())
        baseline=json.loads((root/spec['baselines'][str(seconds)]/'report.json').read_text())
        assert report['records']==baseline['records']
        manifest=json.loads((path/'dataset-manifest.json').read_text())
        dataset=path/'history-state-pairs.npz';assert digest(dataset)==manifest['dataset_sha256']
        with np.load(dataset) as z:
            assert z['history'].shape==(150,90,2055) and z['target'].shape==(150,90,8)
            rows,training,active=z['initial_rows'],z['train_rows'],z['active']
            assert np.array_equal(training,rows%100<20)
            assert np.array_equal(rows,np.array([b+i for b in [0,100,200] for i in range(30)]))
            assert np.array_equal(z['step'],np.arange(0,600,4))
            assert np.isfinite(z['history']).all() and np.isfinite(z['target']).all()
            assert int((active & training[None,:]).sum())==manifest['train_samples']==9000
            assert int((active & ~training[None,:]).sum())==manifest['validation_samples']==4500
        result['collections'].append(dict(seconds=seconds,runtime=runtime,formal=metrics,
            baseline_records_equal=True,dataset_sha256=digest(dataset),training_rows=rows[training].tolist(),
            validation_rows=rows[~training].tolist()))
    for name,updates in [('preflight',2),('fitting',1000)]:
        status=json.loads((folder/name/'status.json').read_text());assert status['status']=='completed'
        checks=[]
        for arm in ['teacher_only','aggregated']:
            initial_path=folder/name/f'{arm}-update0000.pth'
            first=torch.load(initial_path,map_location='cpu')
            assert tensor_digest(first['state_encoder'])==initial_tensor
            assert not first['optimizer']['state']
            path=folder/name/f'{arm}-update{updates:04d}.pth'
            final=torch.load(path,map_location='cpu')
            assert digest(path)==json.loads(path.with_suffix('.json').read_text())['sha256']
            assert final['update']==updates
            assert final['teacher_sha256']==artifact['teacher_sha256']
            assert tensor_digest(final['state_encoder'])!=initial_tensor
            counters={int(x['step']) for x in final['optimizer']['state'].values()}
            assert counters=={updates}
            assert status['supervised_counts'][arm]==512*updates
            assert final['fitting_provenance']['validation_excluded']
            checks.append(dict(arm=arm,actual_optimizer_steps=updates,supervised_samples=512*updates,
                initial_tensors_equal=True,fresh_optimizer=True,final_sha256=digest(path)))
        result['fits'].append(dict(name=name,status_counter=status['updates_completed'],checks=checks))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(collection_records_equal=True,formal_fit_updates=1000,preflight_actual_updates=2,
        validation_excluded=True,initial_tensors_equal=True)))


if __name__=='__main__':main()
