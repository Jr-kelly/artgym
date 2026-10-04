"""Offline causal PD damping ablation; actual pair force is evaluation only."""
import argparse, json
from pathlib import Path
import numpy as np
import torch
from scripts.wuji_joint_deflection_pressure import BatchedJointDeflectionPressure


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    tr=np.load(a.trial/'trace.npz')
    physics=json.loads((a.trial/'physics.json').read_text())
    command=json.loads((a.trial/'plan.json').read_text())['args']
    cal=json.loads(Path(command['handover_calibration']).read_text())
    normal=np.asarray(cal['object_in_wrist'])[:3,1]
    ids=physics['hand_indices'];kp=np.asarray(physics['kp'])[ids]
    kd=np.asarray(physics['kd'])[ids][16:]
    spec=json.loads(Path(command['proprioceptive_pressure_config']).read_text())
    model=BatchedJointDeflectionPressure(spec,1,'cpu',kp)
    model.reset(torch.tensor([0]),torch.tensor(normal,dtype=torch.float32)[None])
    rows=[]
    for i in range(1,len(tr['time'])):
        # Native rows record pre-step measured q and post-command targets.
        # The preceding row is the already issued target at this invocation.
        q=tr['observed_q'][i];issued=tr['target'][i-1,ids]
        first=max(0,i-5);delta=tr['time'][i]-tr['time'][first]
        velocity=(q[16:]-tr['observed_q'][first,16:])/delta
        jac=model.model(torch.tensor(q,dtype=torch.float32)[None],
                        torch.tensor(issued,dtype=torch.float32)[None])[0].numpy()
        damping_force=np.linalg.solve(jac@jac.T+np.eye(3)*1e-7,jac@(-kd*velocity))
        original=float(model.last_estimate[0]);corrected=original-float(damping_force@normal)
        rows.append([tr['time'][i],original,corrected,
                     tr['estimated_thumb_pressure_N'][i],tr['pair_slider_pressure_mean_N'][i,0]])
    rows=np.asarray(rows);results=[]
    for phase,lo,hi in [('hold',14,16),('extend1',16,21),('return1',21,26),
                        ('extend2',26,31),('return2',31,36)]:
        s=rows[(rows[:,0]>=lo)&(rows[:,0]<hi)]
        results.append(dict(phase=phase,
            replay_estimate_agreement_rmse_N=float(np.sqrt(np.mean((s[:,1]-s[:,3])**2))),
            static_model_vs_pairnormal_rmse_N=float(np.sqrt(np.mean((s[:,1]-s[:,4])**2))),
            damping_model_vs_pairnormal_rmse_N=float(np.sqrt(np.mean((s[:,2]-s[:,4])**2))),
            signed_damping_model_change_mean_N=float(np.mean(s[:,2]-s[:,1]))))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(rows=results,
        scope='Offline ablation on existing native episode. Inputs to each model are measured q, preceding issued targets, original PD gains, fixed initial normal and five-frame causal q difference. Pair normal is evaluation truth only. No force-sensor/normalcalibration claim; inertia/contact friction not identified.',
        online_control_changed=False),indent=2)+'\n')
    np.savez_compressed(a.output.with_suffix('.npz'),time_s=rows[:,0],static_proxy_N=rows[:,1],
                        damping_proxy_N=rows[:,2],recorded_proxy_N=rows[:,3],actual_pair_normal_N=rows[:,4])
    print(json.dumps(results))


if __name__=='__main__':main()
