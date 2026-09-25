"""Fit a small affine latent calibration on teacher-driven training trajectories.

This is a new supervised student variant. Its fit/validation split is by full
environment trajectory, not interleaved frames. No physical success is inferred
from regression error; subsequent pure-student closed-loop tests are required.
"""
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    folder=base/'diagnostics/student-cp500-calibration-training32'
    status=json.loads((folder/'status.json').read_text())
    assert status['status']=='completed' and status['returncode']==0
    metadata=json.loads((folder/'encoder_report.json').read_text())
    assert len(metadata['students'])==1
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert metadata['students'][0]['sha256']=='7afa3e41d1574e09b4cc6519e6af502ea598d6885d75b8318f0b30b27f6ef9b0'
    with np.load(folder/'encoder_error_trace.npz') as loaded:
        target=loaded['teacher_latent'].astype(np.float64)
        predicted=target+loaded['latent_error'][:,0].astype(np.float64)
        active=loaded['active'].astype(bool)
    assert predicted.shape==target.shape==(600,32,16)
    splits={'fit':slice(0,24),'validation':slice(24,32)}
    pairs={k:(predicted[:,s][active[:,s]],target[:,s][active[:,s]]) for k,s in splits.items()}
    x,y=pairs['fit'];xv,yv=pairs['validation']
    center=x.mean(0);scale=np.maximum(x.std(0),1e-6);ymean=y.mean(0)
    normalized=(x-center)/scale
    choices=[]
    for ridge in [0.0001,0.001,0.01,0.1,1.0,10.0]:
        w=np.linalg.solve(normalized.T@normalized/len(x)+ridge*np.eye(16),normalized.T@(y-ymean)/len(x))
        raw_w=w/scale[:,None];bias=ymean-center@raw_w
        choices.append(dict(ridge=ridge,weight=raw_w.astype(np.float32).tolist(),bias=bias.astype(np.float32).tolist(),
            fit_mse=float(np.mean((x@raw_w+bias-y)**2)),validation_mse=float(np.mean((xv@raw_w+bias-yv)**2))))
    best=min(choices,key=lambda c:(c['validation_mse'],-c['ridge']))
    out=base/'frozen-candidates/student-cp500-affine-calibration-seed53';out.mkdir(exist_ok=False)
    result=dict(status='frozen',scope=__doc__,teacher_sha256=metadata['teacher_sha256'],student_sha256=metadata['students'][0]['sha256'],
        training_initial_states_sha256=json.loads((base/'student-calibration-training-seed20261053/manifest.json').read_text())['states_sha256'],
        training_trace_sha256=sha(folder/'encoder_error_trace.npz'),physical_seed=1616,fit_environment_rows=list(range(24)),
        validation_environment_rows=list(range(24,32)),fit_samples=len(x),validation_samples=len(xv),
        baseline_mse={k:float(np.mean((a-b)**2)) for k,(a,b) in pairs.items()},selected=best,candidates=choices,
        deployment_inputs='Only the frozen base student latent from proprioception/history and initial observation; no current privileged state.',
        sources={str(p.relative_to(root)):sha(p) for p in [Path(__file__),folder/'probe_source.py',folder/'encoder_report.json',folder/'status.json']})
    (out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(dict(artifact='calibration.json',sha256=sha(out/'calibration.json'),scope=__doc__),indent=2)+'\n')
    print(json.dumps(dict(output=str(out),baseline=result['baseline_mse'],selected={k:best[k] for k in ['ridge','fit_mse','validation_mse']})))


if __name__=='__main__':main()
