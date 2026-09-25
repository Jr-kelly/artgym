"""Sensor-only Wuji RGB inference without constructing a physics environment.

Inputs are RGB, encoder joints, an external slider goal, and reset-only known
geometry. This module does not connect to or command hardware. Camera pose,
actuator timing, initial-pose measurement and physical calibration remain
external requirements; simulation parity does not establish hardware safety.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from scripts.wuji_rgb_state_model import RGBStateModel, OUTPUT_SCALES
from scripts.wuji_physical_state_encoder import decode_prediction, SCALES
from scripts.wuji_kinematics import WujiKinematics
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from isaacgymenvs.utils.torch_jit_utils import scale, unscale
from omegaconf import OmegaConf


class WujiRGBPolicyRuntime:
    def __init__(self,cfg,teacher_path,rgb_path,control_dt=1/30):
        teacher_path=Path(teacher_path);rgb_path=Path(rgb_path)
        self.artifact_sha256=hashlib.sha256(rgb_path.read_bytes()).hexdigest()
        assert self.artifact_sha256==json.loads(rgb_path.with_suffix('.json').read_text())['sha256']
        artifact=torch.load(rgb_path,map_location='cpu')
        assert artifact['update']==5000 and artifact['arm'] in ['rgb','masked']
        teacher_sha=hashlib.sha256(teacher_path.read_bytes()).hexdigest()
        assert all(row['teacher_sha256']==teacher_sha for row in artifact['provenance']['sources'])
        self.arm=artifact['arm'];self.cfg=cfg;self.dt=float(control_dt)
        assert abs(self.dt-1/30)<1e-7
        config=preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True))
        self.player=build_policy_player(cfg,config,teacher_path,_infer_expl_num_blocks(teacher_path),0)
        self.device=self.player.device
        self.estimator=RGBStateModel(artifact['feature_mean'],artifact['feature_scale']).to(self.device).eval()
        self.estimator.load_state_dict(artifact['state_dict'])
        for model in [self.player.model,self.estimator]:
            for parameter in model.parameters():parameter.requires_grad_(False)
        self.fk=WujiKinematics()
        self.lower=torch.as_tensor(self.fk.lower,dtype=torch.float32,device=self.device)
        self.upper=torch.as_tensor(self.fk.upper,dtype=torch.float32,device=self.device)
        props=cfg.object.default_props
        self.properties=torch.tensor(list(props.mass)+[props.friction,props.dof_damping,props.get('dof_stiffness',0.)],
                                     dtype=torch.float32,device=self.device).reshape(1,5)
        self.support_span=float(cfg.task.env.supportActionSpan)
        self.thumb_step=float(cfg.task.env.thumbActionStep)
        self.moving_average=float(cfg.task.env.actionsMovingAverage)
        assert not cfg.task.env.useRelativeControl
        self.initial=None

    def tensor(self,value,width,name):
        x=torch.as_tensor(value,dtype=torch.float32,device=self.device)
        if x.ndim==1:x=x[None]
        assert x.ndim==2 and x.shape[1]==width and torch.isfinite(x).all(),name
        return x.clone()

    def reset(self,known_initial,initial_joint_targets):
        self.initial=self.tensor(known_initial,55,'reset-only geometry')
        self.initial_targets=self.tensor(initial_joint_targets,20,'initial joint targets')
        assert len(self.initial)==len(self.initial_targets)
        self.previous_targets=self.initial_targets.clone()
        self.previous_action=torch.zeros_like(self.initial_targets)
        self.values=self.initial.new_zeros((len(self.initial),8));self.step=0
        init_player_rnn_for_batch(self.player,len(self.initial))

    @torch.no_grad()
    def infer(self,joints,rgb,goal_offset,applied_previous_action=None,commanded_previous_targets=None):
        assert self.initial is not None,'reset required'
        # A shadow controller must consume the commands actually sent by the
        # driver. In autonomous use, these default to our own prior outputs.
        if applied_previous_action is not None:
            self.previous_action=self.tensor(applied_previous_action,20,'last applied normalized action')
        if commanded_previous_targets is not None:
            self.previous_targets=self.tensor(commanded_previous_targets,20,'last commanded joint targets')
        q=self.tensor(joints,20,'encoder joint radians');goal=self.tensor(goal_offset,1,'external slider goal metres')
        assert len(q)==len(goal)==len(self.initial)
        qnorm=2*(q-self.lower)/(self.upper-self.lower)-1
        tips=[]
        for row in q.cpu().numpy():
            frames=self.fk.forward(row)
            tips.append(np.concatenate([frames[name][:3,3] for name in self.fk.config['track_links']]))
        tips=self.tensor(np.asarray(tips),15,'FK pad origins')
        if self.step==0:tips=self.initial[:,34:49].clone()
        features=torch.cat([self.initial,qnorm,self.previous_action,goal],-1)
        if self.step==0:
            assert rgb is None,'initial control uses the declared known reset state'
            values=torch.zeros_like(self.values)
        else:
            images=np.asarray(rgb)
            assert images.dtype==np.uint8 and images.shape==(len(q),320,320,3)
            image=torch.as_tensor(images,device=self.device).permute(0,3,1,2).float()/255.-.5
            prediction=self.estimator(image,features,mask_image=self.arm=='masked')*features.new_tensor(OUTPUT_SCALES)
            velocity=.75*self.values[:,7]+.25*(prediction[:,6]-self.values[:,6])/self.dt
            values=torch.cat([prediction,velocity[:,None]],-1)
        physical=decode_prediction(self.initial,values/values.new_tensor(SCALES),self.properties)
        policy=torch.cat([features,tips],-1)
        # Five critic-only contact fields are zero; exploration block is the
        # same deterministic coefficient used by the frozen teacher evaluator.
        obs=torch.cat([policy,physical,policy.new_zeros((len(policy),5))],-1)
        if self.player.intr_reward_coef_embd is not None:
            coef=self.player.intr_reward_coef_embd[:1].expand(len(policy),-1)
            obs=torch.cat([obs,coef],-1)
        action=self.player.get_action(obs,is_deterministic=True)
        targets=self.initial_targets+self.support_span*action
        targets[:,16:20]=self.previous_targets[:,16:20]+self.thumb_step*action[:,16:20]
        targets=torch.maximum(torch.minimum(targets,self.upper),self.lower)
        # WujiAcquisition -> WujiDemoAligned -> ArtManip converts targets to
        # normalized commands and back, then applies smoothing and limits.
        # Preserve that exact FP32 chain: its tiny roundoff otherwise accrues
        # in the incremental thumb's stored previous target during autonomous
        # control. This is controller arithmetic, never a sensor correction.
        normalized=unscale(targets,self.lower,self.upper)
        desired=scale(normalized,self.lower,self.upper)
        targets=self.moving_average*desired+(1-self.moving_average)*self.previous_targets
        targets=torch.maximum(torch.minimum(targets,self.upper),self.lower)
        assert torch.isfinite(action).all() and torch.isfinite(targets).all()
        self.previous_action=action.clone();self.previous_targets=targets.clone();self.values=values.clone();self.step+=1
        return dict(action=action.clone(),joint_targets=targets.clone(),estimated_state=values.clone(),policy_observation=policy.clone())
