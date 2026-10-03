"""Actual pre-operation sensing prefixes; no new controller or geometry inputs."""
import argparse,pathlib,json,hashlib
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic
import numpy as np
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument("--output-base",type=pathlib.Path,required=True);p.add_argument("--split",choices=["train","fresh"],required=True);p.add_argument("--seed",type=int,required=True);a=p.parse_args();torch.set_num_threads(4)
 checkpoint=pathlib.Path("runs/robust-knife-family-20261003/train/geometric-P1/update_000050.pth");saved=torch.load(checkpoint,map_location="cuda")
 for seconds in [8,16]:
  out=a.output_base/f"context-prefix{seconds}-{a.split}-v1";out.mkdir(parents=True,exist_ok=False);scene=G2ContinuousScene(n=512,seed=a.seed,randomization_scale=1,reference_spec=saved["thumb_reference"],takeover_seconds=seconds,load_profile="mixed",load_frequency=1.7,load_max=.5,detent_max=.5)
  model=ResidualActorCritic(154,181).to("cuda");model.load_state_dict(saved["model"]);model.eval();initial={k:v.cpu().numpy().copy() for k,v in {"root":scene.root,"dof":scene.dof,"materials":scene.material_tensor,"observation_bias":scene.observation_bias,"delay":scene.delay,"cal_object":scene.cal_object,"cal_slider":scene.cal_slider,"load_amplitude":scene.load_amplitude,"detent_amplitude":scene.detent_amplitude,"load_phase":scene.load_phase}.items()};np.savez_compressed(out/"initial-snapshot.npz",**initial);targets=[];qs=[]
  try:
   for step in range(seconds*30):
    public,_=scene.features();assert not scene.policy_active.any();scene.step(torch.zeros((512,20),device="cuda"),torch.tensor(saved["action_scale"],device="cuda"),reset_failed=False,reset_finished=False)
    if step<240:targets.append(scene.target.cpu().numpy().copy());qs.append(scene.dof[:,scene.hand_ids,0].cpu().numpy().copy())
   public,_=scene.features();assert scene.policy_active.all() and (scene.age==seconds*30).all();packet=scene.bridge.last_encoder_input.cpu().numpy();legal=torch.cat([public[:,:131],public[:,151:154]],-1).cpu().numpy();assert packet.shape==(512,2076) and legal.shape==(512,134)
   np.savez_compressed(out/"data.npz",packets=packet,features=legal,groups=np.arange(512,dtype=np.int32),times=np.full(512,seconds,np.float32));np.savez_compressed(out/"prefix-trace.npz",target=np.stack(targets),q=np.stack(qs));rows=[{"env":i,"instance":scene.instances[i],"prefix_seconds":seconds,"height_at_capture_m":float(scene.rb[i,scene.object_index,2]-scene.origins[i,2]),"pickup_valid":(bool(scene.min_hold_height[i]>.78) and bool(scene.closed_at_handover[i])) if seconds==16 else False,"pickup_metric_scope":"At8 onlyapproach/close completed; pickup_valid not applicable and encodedFalse, never counted as pickupfailure"} for i in range(512)];(out/"episodes.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
   j={"seed":a.seed,"seconds":seconds,"n":512,"physical_instances":scene.instances,"physical_asset_parameters":scene.asset_records,"checkpoint_sha256":hashlib.sha256(checkpoint.read_bytes()).hexdigest(),"data_sha256":hashlib.sha256((out/"data.npz").read_bytes()).hexdigest(),"scope":"ActualTABLE originalscriptprefix andlegal50 measuredq/actionhistory atfirsttakeover, beforeanyresidualaction. No slideroperation/fullsuccess claim. Truth only diagnostics/geometrylabels, never inputs."};(out/"report.json").write_text(json.dumps(j,indent=2));print(json.dumps({"seconds":seconds,"n":512,"output":str(out),"data_sha256":j["data_sha256"]}),flush=True)
  finally:scene.close()
  del scene,model;torch.cuda.empty_cache()
if __name__=="__main__":main()
