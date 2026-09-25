"""Independently verify sensor interventions and rescore every recorded physical endpoint."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace

ROOT = Path(__file__).resolve().parents[1]
MODES = ['full','position_bias_0p5mm','position_bias_2mm','rotation_bias_0p5deg',
         'rotation_bias_2deg','slider_bias_0p25mm','slider_bias_1mm','delay1','delay3','delay6']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=int,nargs='+',choices=[2,5],required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    assert not args.output.exists()
    results=[]
    for sec in args.seconds:
        root=ROOT/'runs/wuji-goal/diagnostics'/('teacher-sensor-%ds-1957-v1'%sec)
        state=json.loads((root/'status.json').read_text())
        assert state['status']=='completed'
        assert len(state['stages'])==20 and all(s['returncode']==0 for s in state['stages'])
        for runtime in [True,False]:
            for mode in MODES:
                folder=root/(('runtime-' if runtime else '')+mode)
                report=json.loads((folder/'report.json').read_text())
                audit=json.loads((folder/'input-probe-report.json').read_text())
                assert audit['status']=='passed' and audit['weights_unchanged']
                with np.load(folder/'trace.npz') as z:
                    trace={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
                rescored=score_timed_trace(trace,report['protocol']['stage_steps'],9,600)
                assert rescored['records']==report['records']
                with np.load(folder/'input-trace.npz') as z:
                    true=z['true_privileged'].astype(np.float64)
                    actor=z['actor_privileged'].astype(np.float64)
                    active=z['active']
                count=report['num_envs']*report['recorded_steps']
                assert audit['actual_physics_transitions']==count
                assert true.shape==actor.shape==(report['recorded_steps'],report['num_envs'],21)
                checks={}
                if mode=='full':
                    assert np.array_equal(true,actor)
                elif mode.startswith('delay'):
                    lag=int(mode[-1])
                    indices=np.maximum(np.arange(len(true))-lag,0)
                    # Link pose is coherently reconstructed, but base/articulation
                    # and physical parameters must be exact delayed measurements.
                    subset=[0,1,2,3,4,5,6,14,15,16,17,18,19,20]
                    assert np.array_equal(actor[:,:,subset],true[indices][:,:,subset])
                    checks['exact_delay_steps']=lag
                    checks['maximum_link_reconstruction_m']=float(np.abs(actor[:,:,7:10]-true[indices][:,:,7:10]).max())
                elif mode.startswith('position_bias'):
                    distance=.0005 if mode=='position_bias_0p5mm' else .002
                    diff=actor[:,:,:3]-true[:,:,:3]
                    assert np.allclose(np.linalg.norm(diff,axis=-1),distance,rtol=0,atol=1e-7)
                    assert np.max(np.abs(diff-diff[:1]))<1e-7
                    assert np.array_equal(actor[:,:,3:7],true[:,:,3:7])
                    assert np.array_equal(actor[:,:,14:],true[:,:,14:])
                    checks['maximum_bias_length_error_m']=float(np.abs(np.linalg.norm(diff,axis=-1)-distance).max())
                elif mode.startswith('rotation_bias'):
                    angle=np.deg2rad(.5 if mode=='rotation_bias_0p5deg' else 2.)
                    a=actor[:,:,3:7];b=true[:,:,3:7]
                    dot=np.abs(np.sum(a*b,axis=-1)/(np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1)))
                    actual=2*np.arccos(np.clip(dot,0,1))
                    assert np.max(np.abs(actual-angle))<2e-5
                    assert np.array_equal(actor[:,:,:3],true[:,:,:3])
                    assert np.array_equal(actor[:,:,14:],true[:,:,14:])
                    checks['maximum_rotation_magnitude_error_rad']=float(np.abs(actual-angle).max())
                elif mode.startswith('slider_bias'):
                    distance=.00025 if mode=='slider_bias_0p25mm' else .001
                    diff=actor[:,:,19]-true[:,:,19]
                    assert np.allclose(np.abs(diff),distance,rtol=0,atol=1e-7)
                    assert np.max(np.abs(diff-diff[:1]))<1e-7
                    assert np.array_equal(actor[:,:,:7],true[:,:,:7])
                    assert np.array_equal(actor[:,:,14:19],true[:,:,14:19])
                    assert np.array_equal(actor[:,:,20],true[:,:,20])
                    checks['maximum_slider_bias_error_m']=float(np.abs(np.abs(diff)-distance).max())
                body=(np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
                      (trace['drift']<.01) & (trace['rotation']<.25)).all(0)
                alive=np.array([r['alive_full'] for r in report['records']])
                body &= alive
                groups=[]
                slices=[(0,1),(1,2),(2,3)] if runtime else [(0,100),(100,200),(200,300),(300,332)]
                for lo,hi in slices:
                    records=report['records'][lo:hi]
                    groups.append(dict(count=hi-lo,joint=sum(r['stable_full_all_endpoints'] for r in records),
                        alive=int(alive[lo:hi].sum()),body=int(body[lo:hi].sum()),
                        all_endpoints=sum(r['all_endpoints_held'] for r in records)))
                results.append(dict(seconds=sec,mode=mode,runtime=runtime,groups=groups,
                    recorded_steps=report['recorded_steps'],actual_transitions=count,
                    joint=report['stable_full_all_endpoints'],alive=report['alive_full'],body=int(body.sum()),
                    intervention_rms=np.sqrt(np.mean((actor[active]-true[active])**2,axis=0)).tolist(),
                    checks=checks,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [folder/'report.json',folder/'trace.npz',folder/'input-trace.npz',folder/'input-probe-report.json']}))
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        records_rescored_exact=True,interventions_independently_checked=True,rows=results,
        runtime_transitions=sum(x['actual_transitions'] for x in results if x['runtime']),
        formal_transitions=sum(x['actual_transitions'] for x in results if not x['runtime']),
        scope='Frozen privileged-teacher sensor-tolerance diagnostic. Reused development states; fixed random direction/sign per environment. Separate interventions, no joint-noise or actual-sensor/hardware claim. Temporal errors differ from constant biases; no inference that proprioception is insufficient.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(seconds=r['seconds'],mode=r['mode'],joint=r['joint'],alive=r['alive'],body=r['body']) for r in results if not r['runtime']]))


if __name__=='__main__':
    main()
