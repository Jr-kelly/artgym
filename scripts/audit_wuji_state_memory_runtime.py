"""Audit real-gradient memory preflight and every completed physics gate."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_state_memory import load_observer,observer_step
from scripts.audit_distillation_runtime import tensor_digest
from scripts.analyze_wuji_state_encoder_evaluations import analyze


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1];torch.set_num_threads(4)
    initial=root/'runs/wuji-goal/diagnostics/state-scale-2036-v1/artifacts/precision_units.pth'
    original=torch.load(initial,map_location='cpu');original_tensor=tensor_digest(original['state_encoder'])
    status=json.loads((args.folder/'preflight/status.json').read_text())
    assert status['status']=='completed' and status['updates_completed']==2 and status['optimizer_counters_verified']
    assert status['supervised_samples_each']==4800 and status['causal_sensor_frames_each']==19104
    with np.load(root/'runs/wuji-goal/diagnostics/state-scale-2036-v1/collection/history-state-pairs.npz') as z:
        x=torch.from_numpy(z['history'][15,[0,10,20,40]].copy())
    checks=[];initial_hashes=[]
    for arm in ['persistent','reset_each_step']:
        first=torch.load(args.folder/'preflight'/f'{arm}-update0000.pth',map_location='cpu')
        path=args.folder/'preflight'/f'{arm}-update0002.pth';artifact=torch.load(path,map_location='cpu')
        assert digest(path)==json.loads(path.with_suffix('.json').read_text())['sha256']
        assert tensor_digest(first['state_encoder'])==tensor_digest(artifact['state_encoder'])==original_tensor
        initial_hashes.append(tensor_digest(first['memory_encoder']))
        assert not first['memory_optimizer']['state']
        assert {int(v['step']) for v in artifact['memory_optimizer']['state'].values()}=={2}
        assert tensor_digest(first['memory_encoder'])!=tensor_digest(artifact['memory_encoder'])
        base,observer=load_observer(artifact,'cpu')
        zero=torch.zeros(1,4,64);one=torch.ones(1,4,64)
        with torch.no_grad():
            a,_,_=observer_step(base,observer,x,zero,arm)
            b,_,_=observer_step(base,observer,x,one,arm)
        difference=float((a-b).abs().max())
        assert (difference>0)==(arm=='persistent')
        checks.append(dict(arm=arm,optimizer_steps=2,weights_changed=True,base_frozen=True,
            same_input_different_incoming_memory_max=difference,artifact_sha256=digest(path)))
    assert initial_hashes[0]==initial_hashes[1]
    formal_checks=[]
    if (args.folder/'fitting/status.json').exists():
        formal_status=json.loads((args.folder/'fitting/status.json').read_text())
        assert formal_status['status']=='completed' and formal_status['updates_completed']==1000
        assert formal_status['supervised_samples_each']==2400000 and formal_status['causal_sensor_frames_each']==9552000
        for arm in ['persistent','reset_each_step']:
            initial_path=args.folder/'fitting'/f'{arm}-update0000.pth'
            first=torch.load(initial_path,map_location='cpu')
            assert tensor_digest(first['memory_encoder'])==initial_hashes[0]
            assert not first['memory_optimizer']['state']
            path=args.folder/'fitting'/f'{arm}-update1000.pth';artifact=torch.load(path,map_location='cpu')
            assert digest(path)==json.loads(path.with_suffix('.json').read_text())['sha256']
            assert tensor_digest(artifact['state_encoder'])==original_tensor
            assert {int(v['step']) for v in artifact['memory_optimizer']['state'].values()}=={1000}
            assert artifact['memory_provenance']['supervised_samples']==2400000
            assert torch.equal(first['feature_mean'],artifact['feature_mean']) and torch.equal(first['feature_scale'],artifact['feature_scale'])
            formal_checks.append(dict(arm=arm,actual_optimizer_steps=1000,supervised_samples=2400000,
                causal_frames=9552000,base_frozen=True,fresh_initial_residual_verified=True,artifact_sha256=digest(path)))
    rows=[]
    for folder in sorted(args.folder.glob('gate-*/')):
        if not (folder/'state-estimation-audit.json').exists():continue
        row=analyze(folder);audit=json.loads((folder/'state-estimation-audit.json').read_text())
        assert audit['observer_unchanged']
        assert audit['observer_checks']['committed_steps']==audit['observer_checks']['privacy_memory_checks']==1800
        if row['update']==0:assert audit['observer_checks']['zero_residual_steps']==1800
        rows.append(row)
    result=dict(status='passed',preflight=checks,formal= formal_checks,same_initial_residual_tensors=True,rows=rows,
        complete_runtime_gate_count=len(rows),all8_complete=len(rows)==8,
        scope='Actual2-update preflight plus completed3-state physics gates. Zero head starts at original estimator, both arms fresh; memory intervention verifies persistent dependence and exact reset control. Nottask success.')
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(checks=checks,complete_gates=len(rows))))


if __name__=='__main__':main()
