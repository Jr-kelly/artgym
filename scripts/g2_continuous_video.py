"""Direct camera records of actual continuous-scene physics, all stages."""
import json
from pathlib import Path
import numpy as np
from isaacgym import gymapi


class ContinuousSceneVideo:
    def __init__(self, scene, output, environment_ids):
        import imageio.v2 as imageio
        self.scene=scene;self.output=Path(output);self.cameras=[];self.frames=0
        assert environment_ids and len(set(environment_ids))==len(environment_ids)
        records=[]
        for i in environment_ids:
            assert 0<=i<scene.n
            env=scene.envs[i]
            for name,position,aim,fov in [('continuous',[1.25,-1.4,1.5],[.4,-.3,.85],75),('hand-closeup',[.6415,-.37,1.081],[.3015,-.25,.841],40)]:
                props=gymapi.CameraProperties();props.width=640;props.height=480;props.horizontal_fov=fov
                camera=scene.gym.create_camera_sensor(env,props);assert camera>=0
                scene.gym.set_camera_location(camera,env,gymapi.Vec3(*position),gymapi.Vec3(*aim))
                transform=scene.gym.get_camera_transform(scene.sim,env,camera)
                path=self.output/f'env{i:04d}-{name}.mp4';writer=imageio.get_writer(str(path),fps=30,codec='libx264',quality=7,ffmpeg_params=['-threads','1'])
                self.cameras.append((env,camera,writer));records.append(dict(environment=i,physical_instance=scene.instances[i%len(scene.instances)],file=path.name,requested_position=position,requested_aim=aim,native_camera_transform_position=[transform.p.x,transform.p.y,transform.p.z],environment_origin=scene.origins[i].cpu().tolist(),scope='Nativecameraofthisactualepisode; no resimulation/outcomeselection'))
        self.timeline=(self.output/'video-timeline.jsonl').open('w')
        (self.output/'video-recording.json').write_text(json.dumps(dict(cameras=records,width=640,height=480,fps=30,scope='Actualsamecontinuousphysics evaluation; drawingonly, no state/targetwrites orphysicalassistance.'),indent=2))

    def frame(self, control_step):
        s=self.scene;s.gym.step_graphics(s.sim);s.gym.render_all_camera_sensors(s.sim)
        for env,camera,writer in self.cameras:
            rgb=np.asarray(s.gym.get_camera_image(s.sim,env,camera,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(480,640,4)[...,:3]
            writer.append_data(rgb)
        self.frames+=1;self.timeline.write(json.dumps(dict(control_step=control_step,time_s=(control_step+1)/30))+'\n')

    def close(self):
        for _,_,writer in self.cameras:writer.close()
        self.timeline.close()
