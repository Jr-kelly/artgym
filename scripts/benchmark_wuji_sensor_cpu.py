"""Measure batch-one sensor inference on recorded inputs, without a simulator or hardware."""
from scripts import wuji_goal_common
from pathlib import Path
import hashlib,json,time,platform
import numpy as np
import torch
import imageio.v2 as imageio
from omegaconf import OmegaConf
from isaacgymenvs.deploy.wuji.rgb_policy_runtime import WujiRGBPolicyRuntime
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.audit_distillation_runtime import tensor_digest

def main():
 root=Path(__file__).resolve().parents[1];d=root/'runs/wuji-goal/diagnostics';out=d/'rgb-sensor-cpu-latency-1953-v1';out.mkdir(exist_ok=False)
 run=d/'rgb-sensor-autonomous-driver-1823-v4/runtime-mixed-2s';torch.set_num_threads(1);cfg=OmegaConf.load(run/'config.yaml');cfg.rl_device=cfg.sim_device='cpu';cfg.task.env.numEnvs=1
 artifact=d/'rgb-mixed-fitting-1705-v1/fitting/rgb-update5000.pth';runtime=WujiRGBPolicyRuntime(cfg,root/TEACHER,artifact)
 with np.load(run/'rgb-estimation-trace.npz') as z:initial=z['features'][0,:1,:55].copy();goal=z['features'][1,:1,95:96].copy()
 with np.load(run/'trace.npz') as z:q=z['q'][0,:1].copy()
 states=np.load(root/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy');runtime.reset(initial,states[:1,20:40]);runtime.infer(states[:1,:20],None,goal)
 rgb=imageio.imread(run/'camera-step0001-no-text.png')[:,:320,:3][None];assert rgb.shape==(1,320,320,3)
 before={key:tensor_digest(model.state_dict()) for key,model in [('actor',runtime.player.model),('estimator',runtime.estimator)]}
 for _ in range(50):runtime.infer(q,rgb,goal)
 times=[]
 for _ in range(200):
  start=time.perf_counter();output=runtime.infer(q,rgb,goal);times.append(1000*(time.perf_counter()-start));assert output['action'].shape==(1,20) and torch.isfinite(output['joint_targets']).all()
 after={key:tensor_digest(model.state_dict()) for key,model in [('actor',runtime.player.model),('estimator',runtime.estimator)]};assert before==after
 result=dict(status='completed',device='cpu',threads=1,host=platform.node(),torch=torch.__version__,warmup=50,measured=200,latency_ms=dict(zip(['min','p50','p90','p95','p99','max'],map(float,np.quantile(times,[0,.5,.9,.95,.99,1])))),over_33_333ms=int(np.sum(np.array(times)>1000/30)),model_unchanged=True,models=before,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='CPU batch-one inference, recorded fixed old RGB/encoder inputs, own causal action/target/state history; no simulator construction or hardware commands. Includes CPU FK, image preprocessing, estimator, full actor+critic player, recurrent state and action mapping. Excludes camera exposure/acquisition, network/driver communication and real actuator delay. Concurrent workstation jobs were left running; timing is not a real-hardware deadline guarantee or task-success evaluation.')
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');np.save(out/'latency_ms.npy',np.array(times));(out/'source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(result))
if __name__=='__main__':main()
