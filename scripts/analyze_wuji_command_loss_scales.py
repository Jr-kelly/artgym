"""Quantify command-label units on fixed validation data, without simulation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from scripts.wuji_absolute_target_student import TargetStudent,SCALES


def main():
    root=Path(__file__).resolve().parents[1]
    path=root/'runs/wuji-goal/diagnostics/command-dagger-incremental-1504-v3/training/incremental-update0500.pth'
    artifact=torch.load(path,map_location='cpu')
    model=TargetStudent(artifact['feature_mean'],artifact['feature_scale'])
    model.load_state_dict(artifact['state_dict']);model.eval();torch.set_num_threads(4)
    data=root/'runs/wuji-goal/diagnostics/absolute-target-0048-v2/fitting/data.npz'
    with np.load(data) as z:
        x=z['features'][:,:,~z['training']].reshape(-1,116)
        y=z['incremental'][:,:,~z['training']].reshape(-1,20)
    with torch.no_grad():pred=torch.cat([model(torch.tensor(v)) for v in np.array_split(x,40)]).numpy()
    error=pred-y;physical=error*np.array(SCALES);weights=np.array([1]*16+[12]*4)
    action_error=error*weights
    clipped_error=np.clip(pred*weights,-1,1)-np.clip(y*weights,-1,1)
    result=dict(model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),dataset_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),validation_labels=len(x),
        physical_command_limits=[.04]*16+[.025]*4,output_scales=SCALES,
        normalized_rmse=np.sqrt((error**2).mean(0)).tolist(),joint_command_rmse_rad=np.sqrt((physical**2).mean(0)).tolist(),
        equivalent_unclipped_action_rmse=np.sqrt((action_error**2).mean(0)).tolist(),
        clipped_action_rmse_before_joint_limits=np.sqrt((clipped_error**2).mean(0)).tolist(),
        mean_abs_normalized_gradient=np.abs(np.clip(error/.05,-1,1)).mean(0).tolist(),
        support_action_rmse=float(np.sqrt((clipped_error[:,:16]**2).mean())),
        thumb_action_rmse=float(np.sqrt((clipped_error[:,16:]**2).mean())),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Offline validation, no physics or task success. Incremental thumb action unit=.025rad, current output unit=.3rad. Candidate loss rescales thumb by12 only; actor unchanged.')
    out=root/'runs/wuji-goal/diagnostics/incremental-thumb-loss-scale-audit-1614.json'
    assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
