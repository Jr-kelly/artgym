"""Two fixed ridge fits for slider displacement; no hyperparameter sweep."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_slider_fusion import features,predict_residual
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_physical_state_encoder import SCALES
from scripts.monitor_wuji_checkpoints import atomic_json,now
from scripts.audit_distillation_runtime import tensor_digest


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    manifest=json.loads(args.dataset.with_name('manifest.json').read_text())
    assert digest(args.dataset)==manifest['dataset_sha256'] and digest(args.initial)==manifest['initial_sha256']
    original=torch.load(args.initial,map_location='cpu');before=tensor_digest(original['state_encoder'])
    assert original['phase']=='offline_teacher_fit'
    with np.load(args.dataset) as z:
        sensor=z['features'][:,z['label_steps']].astype(np.float64)
        target=z['target'][...,6].astype(np.float64)/SCALES[6]
        training=z['train_rows'];rows=z['initial_rows'];assert z['active'].all()
    assert sensor.shape==(4,150,90,103) and training.sum()==60
    assert np.array_equal(training,rows%100<20)
    kin=WujiKinematics();results={};base=sensor[...,101]
    residual=target-base
    for arm in ['raw','kinematic']:
        x=features(sensor,kin,arm);train=x[:,:,training].reshape(-1,x.shape[-1])
        y=residual[:,:,training].reshape(-1)
        assert len(train)==len(y)==36000
        mean=train.mean(0);scale=np.maximum(train.std(0),1e-3)
        standardized=np.clip((train-mean)/scale,-10,10)
        design=np.concatenate([standardized,np.ones((len(train),1))],axis=-1)
        regularizer=np.eye(design.shape[-1])*.01;regularizer[-1,-1]=0
        matrix=design.T@design/len(train)+regularizer
        rhs=design.T@y/len(train)
        solution=np.linalg.solve(matrix,rhs)
        # Independent augmented least-squares solve verifies the ridge result.
        augmented=np.concatenate([design/np.sqrt(len(train)),np.sqrt(regularizer)],axis=0)
        independent=np.linalg.lstsq(augmented,np.concatenate([y/np.sqrt(len(train)),np.zeros(design.shape[-1])]),rcond=None)[0]
        error=float(np.max(np.abs(solution-independent)));assert error<1e-8
        weight,bias=solution[:-1],solution[-1]
        predicted=base+predict_residual(x,mean,scale,weight,bias)
        validation={}
        for i,key in enumerate(['teacher2','teacher5','student2','student5']):
            e=(predicted[i][:,~training]-target[i][:,~training])*SCALES[6]
            b=(base[i][:,~training]-target[i][:,~training])*SCALES[6]
            validation[key]=dict(rmse_mm=float(np.sqrt(np.mean(e**2))*1000),
                base_rmse_mm=float(np.sqrt(np.mean(b**2))*1000),bias_mm=float(e.mean()*1000),samples=int(e.size))
        provenance=dict(scope=__doc__,arm=arm,base_sha256=digest(args.initial),dataset_sha256=digest(args.dataset),
            training_rows=rows[training].tolist(),validation_rows=rows[~training].tolist(),validation_excluded=True,
            same_training_samples=36000,ridge_mean_squared_regularization=.01,feature_count=int(x.shape[-1]),
            label='slider displacement residual /0.0005m',no_physics=True,independent_solve_max_error=error,
            no_hyperparameter_selection=True,body_velocity_and_teacher_frozen=True)
        artifact=copy.deepcopy(original)
        artifact.update(phase='offline_slider_fusion',update=1,fitting_provenance=provenance,
            slider_fusion=dict(arm=arm,mean=mean,scale=scale,weight=weight,bias=bias))
        assert tensor_digest(artifact['state_encoder'])==before
        path=args.output/f'{arm}.pth';torch.save(artifact,path)
        atomic_json(path.with_suffix('.json'),dict(sha256=digest(path),created=now(),provenance=provenance))
        results[arm]=dict(validation=validation,provenance=provenance,sha256=digest(path),base_unchanged=True)
    atomic_json(args.output/'status.json',dict(status='completed',finished=now(),arms=results,
        no_success_claim=True,source_sha256=digest(Path(__file__))))
    print(json.dumps(results))


if __name__=='__main__':main()
