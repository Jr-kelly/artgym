"""Asset rendering from measured final hold pose. No physics/task-validation claim."""
from pathlib import Path
import json
from isaacgym import gymapi
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.run_wuji_rear_sim import gt
from scripts.wuji_rear_controller import load_bundle,ROOT

def main():
    spec=load_bundle('research/rear-sim2real-20261009/bundle-deploy-v6.json');out=ROOT/'research/rear-sim2real-20261009/media';out.mkdir(exist_ok=True)
    trace=np.load(ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/trace.npz');i=np.argmin(abs(trace['time']-6.6))
    from scripts.g2_kinematics import G2Kinematics
    wrist=G2Kinematics().forward(trace['arm_q'][i]);obj=np.eye(4);obj[:3,:3]=Rotation.from_quat(trace['object'][i,3:7]).as_matrix();obj[:3,3]=trace['object'][i,:3]
    gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.up_axis=gymapi.UP_AXIS_Z;sim=gym.create_sim(0,0,gymapi.SIM_PHYSX,sp);env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,2),1)
    opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=True
    hand=gym.load_asset(sim,str(ROOT/'assets/hands/wuji_artbot'),'right.urdf',opt);hactor=gym.create_actor(env,hand,gt(wrist),'right_hand',0,0)
    ds=np.zeros(20,dtype=gymapi.DofState.dtype);names=gym.get_actor_dof_names(env,hactor);ds['pos']=[trace['q'][i,spec['runtime_joint_names'].index(n)] for n in names]
    path=ROOT/spec['asset'];knife=gym.load_asset(sim,str(path.parent),path.name,opt);kactor=gym.create_actor(env,knife,gt(obj),'knife',0,0);ks=np.zeros(1,dtype=gymapi.DofState.dtype);ks['pos'][0]=trace['slider'][i]
    cams=[];settings=[];cap=obj@np.r_[0,.005,-.026+trace['slider'][i],1]
    for label,delta,aim,fov in [('front',np.array([.012,.27,.015]),obj[:3,3],40),('side',np.array([.27,.03,.015]),obj[:3,3],40),('thumb-slider',np.array([-.08,.16,.06]),cap[:3],30)]:
        cp=gymapi.CameraProperties();cp.width=1200;cp.height=900;cp.horizontal_fov=fov;cam=gym.create_camera_sensor(env,cp);eye=aim+obj[:3,:3]@delta;gym.set_camera_location(cam,env,gymapi.Vec3(*eye),gymapi.Vec3(*aim));cams.append((label,cam));settings.append(dict(view=label,eye=eye.tolist(),aim=aim.tolist(),horizontal_fov=fov))
    gym.prepare_sim(sim);gym.set_actor_dof_states(env,hactor,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,kactor,ks,gymapi.STATE_ALL);gym.step_graphics(sim);gym.render_all_camera_sensors(sim)
    from PIL import Image
    for label,cam in cams:
        im=np.asarray(gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR),np.uint8).reshape(900,1200,4)[...,:3];Image.fromarray(im).save(out/(label+'.png'))
    (out/'placement-render.json').write_text(json.dumps(dict(scope='Static native asset render from v6 measured hold6.6s; zero simulation steps, no renewed task verification',time_s=float(trace['time'][i]),wrist_world=wrist.tolist(),object_world=obj.tolist(),q_rad=trace['q'][i].tolist(),slider_q_m=float(trace['slider'][i]),camera=settings),indent=2));gym.destroy_sim(sim)
if __name__=='__main__':main()
