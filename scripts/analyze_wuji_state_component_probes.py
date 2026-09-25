"""Independently check component selection, rigid transforms, and physical task scores."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace

SCALES=np.array([.001,.001,.001,.02,.02,.02,.0005,.01])


def multiply(a,b):
    return np.concatenate([a[...,3:]*b[...,:3]+b[...,3:]*a[...,:3]+np.cross(a[...,:3],b[...,:3]),
                           a[...,3:]*b[...,3:]-np.sum(a[...,:3]*b[...,:3],axis=-1,keepdims=True)],axis=-1)


def rotate(q,v):
    t=2*np.cross(q[...,:3],v)
    return v+q[...,3:]*t+np.cross(q[...,:3],t)


def analyze(folder):
    report=json.loads((folder/'report.json').read_text())
    audit=json.loads((folder/'hybrid-state-audit.json').read_text())
    assert audit['status']=='passed' and audit['teacher_unchanged'] and audit['encoder_unchanged']
    condition=audit['condition']
    truth_indices = dict(estimated=[],true_body=list(range(6)),true_slider=[6,7],true_both=list(range(8)),
        true_slider_position=[6],true_slider_velocity=[7],zero_slider_velocity=[])[condition]
    assert audit['current_privileged_actor_input']==bool(truth_indices)
    steps=report['recorded_steps'];n=report['num_envs'];count=steps*n
    assert n in [3,332] and steps==600
    checks=audit['checks']
    assert checks['physics_transitions']==checks['latest_history_matches']==count
    assert checks['actor_input_checks']==count+checks.get('privileged_invariance',0)
    if audit['runtime'] and 'privileged_components' in audit:
        assert audit['privileged_components']==truth_indices
        assert checks['privileged_invariance']==(0 if truth_indices else count)
    if audit['runtime']:
        assert checks['same_state_reference']==count and checks['reference_action_max']==checks['reference_actor_rnn_max']==0
    assert checks['changed_history_rows']>0
    assert checks['kinematic_position_max_m']<5e-5 and checks['kinematic_quaternion_max']<5e-4
    with np.load(folder/'hybrid-trace.npz') as z:
        arrays={k:z[k].astype(np.float64) for k in ['prediction','target','used','actor_privileged','true_privileged','initial']}
        active=z['active']
    prediction,target,used=(arrays[k] for k in ['prediction','target','used'])
    actor,truth,initial=(arrays[k] for k in ['actor_privileged','true_privileged','initial'])
    assert prediction.shape==target.shape==used.shape==(steps,n,8)
    assert actor.shape==truth.shape==(steps,n,21) and initial.shape==(steps,n,55)
    for index in range(8):
        expected = (np.zeros_like(used[...,index]) if condition=='zero_slider_velocity' and index==7 else
                    target[...,index] if index in truth_indices else prediction[...,index])
        assert np.array_equal(used[...,index],expected)
    values=used*SCALES
    rotvec=values[...,3:6];angle=np.linalg.norm(rotvec,axis=-1,keepdims=True)
    rotation=np.concatenate([rotvec*np.sin(angle/2)/np.maximum(angle,1e-8),np.cos(angle/2)],axis=-1)
    quat=multiply(rotation,initial[...,23:27])
    position=initial[...,20:23]+values[...,:3]
    conjugate=initial[...,23:27].copy();conjugate[...,:3]*=-1
    offset=rotate(conjugate,initial[...,27:30]-initial[...,20:23])
    offset[...,1]-=values[...,6]
    link=position+rotate(quat,offset)
    errors=dict(body_position_m=float(np.abs(position-actor[...,:3]).max()),
                quaternion=float(np.abs(quat-actor[...,3:7]).max()),
                link_position_m=float(np.abs(link-actor[...,7:10]).max()),
                articulation=float(np.abs(values[...,6:]-actor[...,19:21]).max()))
    assert max(errors.values())<2e-6,errors
    assert np.array_equal(actor[...,3:7],actor[...,10:14])
    assert np.max(np.abs(actor[...,14:19]-np.array([.029,.006,3.,.3,0.])))<1e-6
    # Independently validate the labels' translation and articulation units.
    true_values=target*SCALES
    assert np.allclose(true_values[...,:3],truth[...,:3]-initial[...,20:23],atol=2e-7,rtol=0)
    assert np.allclose(true_values[...,6:],truth[...,19:21],atol=2e-7,rtol=0)
    with np.load(folder/'trace.npz') as z:
        trace={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
    score=score_timed_trace(trace,report['protocol']['stage_steps'],9,600)
    assert score['records']==report['records']
    body=(np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) & (trace['drift']<.01) & (trace['rotation']<.25)).all(0)
    alive=np.array([x['alive_full'] for x in report['records']]);body &= alive
    groups=[]
    for lo,hi in ([(0,1),(1,2),(2,3)] if n==3 else [(0,100),(100,200),(200,300),(300,332)]):
        records=report['records'][lo:hi]
        error=((prediction-target)*SCALES)[:,lo:hi][active[:,lo:hi]]
        groups.append(dict(count=hi-lo,joint=sum(x['stable_full_all_endpoints'] for x in records),
            endpoints=sum(x['all_endpoints_held'] for x in records),alive=int(alive[lo:hi].sum()),
            body=int(body[lo:hi].sum()),rmse=np.sqrt(np.mean(error**2,axis=0)).tolist()))
    return dict(folder=str(folder),condition=condition,runtime=audit['runtime'],seconds=report['protocol']['stage_seconds'],
        actual_transitions=count,joint=report['stable_full_all_endpoints'],alive=report['alive_full'],body=int(body.sum()),groups=groups,
        component_selection_exact=True,numpy_kinematics_errors=errors,artifact_sha256=audit['student_sha256'],
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [folder/'report.json',folder/'trace.npz',folder/'hybrid-trace.npz',folder/'hybrid-state-audit.json']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folders',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    rows=[analyze(p) for p in args.folders]
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,
        records_rescored_exact=True,component_selection_independently_verified=True,
        scope='Frozen component oracle diagnostic on reused development states. Hybrid controllers use current simulation truth, not deployable success. Kinematics independently checked with NumPy; separate conditions induce different physical trajectories.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(condition=r['condition'],seconds=r['seconds'],runtime=r['runtime'],joint=r['joint'],alive=r['alive'],body=r['body']) for r in rows]))


if __name__=='__main__':
    main()
