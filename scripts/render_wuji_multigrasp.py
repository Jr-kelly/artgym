"""Render the fixed-clock evaluator with the documented front camera only."""
import os
# Single physical GPU 0 on the local rendering host; Vulkan and CUDA agree.
os.environ.pop('CUDA_VISIBLE_DEVICES',None)
os.environ['VK_ICD_FILENAMES']='/etc/vulkan/icd.d/nvidia_icd.json'
from scripts import audit_wuji_multigrasp as audit
original=audit.configuration
def front_camera(*args,**kwargs):
    cfg=original(*args,**kwargs)
    cfg.task.env.camera.cam_pos=[0.,.11,.72]
    cfg.task.env.camera.cam_target=[0.,-.11,.55]
    return cfg
audit.configuration=front_camera
if __name__=='__main__':audit.main()
