"""Rescore every frozen RGB-policy condition and check labels against physics."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-partial',action='store_true')
    p.add_argument('--gates-only',action='store_true',help='Audit explicitly selected runtime/capacity stages, without a task-success claim.')
    args=p.parse_args()
    assert not args.output.exists()
    state=json.loads((args.run/'status.json').read_text());spec=state['spec']
    if not args.allow_partial:assert state['status']=='completed'
    conditions={};audits=[];transitions=0
    initial_path=Path(__file__).resolve().parents[1]/spec.get('initial_states',{}).get('path','runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')
    stage_status={row['name']:row for row in state['stages']}
    for stage in spec['stages']:
        folder=args.run/stage['name']
        process=stage_status.get(stage['name'],{})
        # An audit file written before native shutdown does not certify a
        # successful process. In particular, retain post-rollout SIGSEGVs as
        # failed runs instead of including them in a partial success total.
        if process.get('status')!='completed' or process.get('returncode')!=0:
            assert args.allow_partial,(stage['name'],process)
            continue
        if not (folder/'rgb-policy-audit.json').exists():
            assert args.allow_partial;continue
        report=json.loads((folder/'report.json').read_text())
        audit=json.loads((folder/'rgb-policy-audit.json').read_text())
        assert audit['status']=='passed' and audit['model_unchanged'] and audit['estimator_unchanged']
        assert not audit['current_truth_actor_input']
        assert audit['artifact_sha256']==spec['artifacts'][stage['arm']]['sha256']
        selected=stage.get('initial_state_rows',[0,100,200] if stage.get('runtime_check') else list(range(332)))
        assert report['initial_state_rows']==selected and report['num_envs']==len(selected)
        assert audit['checks']['physics_transitions']==600*len(selected)
        assert audit['checks']['camera_frames']==599*len(selected)
        if spec.get('initial_states'):assert hashlib.sha256(initial_path.read_bytes()).hexdigest()==spec['initial_states']['sha256']
        assert hashlib.sha256(initial_path.read_bytes()).hexdigest()==report['initial_states_sha256']
        initial=np.load(initial_path)[selected]
        with np.load(folder/'trace.npz') as z:trace={k:z[k] for k in z.files}
        with np.load(folder/'rgb-estimation-trace.npz') as z:est={k:z[k] for k in z.files}
        assert trace['slider'].shape==(600,len(selected))
        if spec.get('sensor_active_parity'):
            assert audit['sensor_active_parity'] and report['sensor_active_parity']
            assert np.array_equal(est['active'].astype(bool),trace['active'].astype(bool))
            active_count=int(est['active'].sum());retired_count=est['active'].size-active_count
            assert audit['checks']['sensor_active_rows']==active_count
            assert audit['checks']['sensor_retired_rows']==retired_count
            assert audit['checks']['sensor_retired_ids']==np.flatnonzero(~est['active'].astype(bool).all(axis=0)).tolist()
        rescored=score_timed_trace(trace,report['protocol']['stage_steps'],9,600)
        assert rescored['records']==report['records']
        active=est['active'][1:].astype(bool)&trace['active'][:-1].astype(bool)
        # Independent time alignment: pre-action labels equal prior post-physics state.
        alignment=dict(slider_m=float(np.abs(est['truth'][1:,:,6]+initial[None,:,54]-trace['slider'][:-1])[active].max()),
            translation_m=float(np.abs(np.linalg.norm(est['truth'][1:,:,:3],axis=-1)-trace['drift'][:-1])[active].max()),
            rotation_rad=float(np.abs(np.linalg.norm(est['truth'][1:,:,3:6],axis=-1)-trace['rotation'][:-1])[active].max()),
            previous_action=float(np.abs(est['features'][1:,:,75:95]-trace['action'][:-1])[active].max()),
            external_goal_m=float(np.abs(est['features'][:,:,95]+initial[None,:,54]-trace['goal'])[est['active'].astype(bool)].max()))
        assert alignment['slider_m']<1e-6 and alignment['translation_m']<1e-6 and alignment['rotation_rad']<1e-5,alignment
        assert alignment['previous_action']==0 and alignment['external_goal_m']<1e-7,alignment
        assert np.max(np.abs(est['prediction'][0]))==0
        assert np.max(np.abs(est['truth'][0,:,:7]))<1e-6
        dt=report['protocol']['control_dt'];pred=est['prediction']
        velocity=np.zeros_like(pred[:,:,7])
        for t in range(1,600):velocity[t]=.75*velocity[t-1]+.25*(pred[t,:,6]-pred[t-1,:,6])/dt
        assert np.allclose(velocity,pred[:,:,7],atol=1e-6)
        pure_body=np.all(trace['active'].astype(bool)&~trace['fall'].astype(bool)&~trace['invalid'].astype(bool)
            &np.isfinite(trace['drift'])&np.isfinite(trace['rotation'])&(trace['drift']<.01)&(trace['rotation']<.25),axis=0)
        key=stage['name'] if args.gates_only else stage['arm']+'-'+str(stage['seconds'])+'s'
        target=conditions.setdefault(key,dict(arm=stage['arm'],seconds=stage['seconds'],records={},files=[]))
        for local,index in enumerate(selected):
            assert str(index) not in target['records']
            target['records'][str(index)]=dict(rescored['records'][local],body_only=bool(pure_body[local]))
        target['files'].append(stage['name'])
        transitions+=600*len(selected)
        audits.append(dict(stage=stage['name'],alignment=alignment,hashes={name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
            for name in ['report.json','trace.npz','rgb-estimation-trace.npz','rgb-policy-audit.json']}))
    for key,condition in conditions.items():
        records=condition['records'];condition['groups']=[]
        if not args.allow_partial and not args.gates_only:assert set(map(int,records))==set(range(332))
        for start,end in [(0,100),(100,200),(200,300),(300,332)]:
            group=[records[str(i)] for i in range(start,end) if str(i) in records]
            condition['groups'].append(dict(initial_rows=[start,end],evaluated=len(group),
                joint=sum(x['stable_full_all_endpoints'] for x in group),body=sum(x['body_only'] for x in group),
                endpoints=sum(x['all_endpoints_held'] for x in group),alive=sum(x['alive_full'] for x in group)))
        condition['training300_success']=sum(g['joint'] for g in condition['groups'][:3])
        condition['training300_evaluated']=sum(g['evaluated'] for g in condition['groups'][:3])
    if not args.allow_partial:
        if args.gates_only:assert len(audits)==len(spec['stages'])
        else:
            expected_keys={f'{arm}-{seconds}s' for arm in spec['artifacts'] for seconds in [2,5]}
            assert set(conditions)==expected_keys
            assert len(audits)==4*len(expected_keys) and transitions==len(expected_keys)*332*600
    result=dict(status='verified_partial' if args.allow_partial else 'verified_runtime_gates' if args.gates_only else 'verified_complete',conditions=conditions,
        audits=audits,physics_transitions=transitions,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        initial_states_sha256=hashlib.sha256(initial_path.read_bytes()).hexdigest(),
        artifacts=spec['artifacts'],evaluation_seed=spec.get('evaluation_seed',20261060),
        scope=spec.get('scope','Frozen RGB/masked models, four matched83state chunks per332state clock. Reused development data; no independent or hardware success.'))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:dict(success=v['training300_success'],evaluated=v['training300_evaluated']) for k,v in conditions.items()}))


if __name__=='__main__':main()
