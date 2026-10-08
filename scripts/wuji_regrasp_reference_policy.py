"""Native controller for the contact-changing short policy, not the push actor."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.train_wuji_regrasp import RegraspActor
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_pose_motion import PoseMotion
from scripts.wuji_regrasp_contract import phase_increment, PAUSE_TIMING, LEGACY_TIMING

class RegraspReferencePolicy:
    def __init__(self,spec,output):
        self.spec=spec;self.output=Path(output);self.kin=G2Kinematics();self.phase=0.
        checkpoint=Path(spec['checkpoint']);saved=torch.load(checkpoint,map_location='cpu')
        assert saved['format'] in ['wuji-regrasp-reference-ppo-v1','wuji-regrasp-reference-ppo-v2','wuji-regrasp-fresh-ppo-v3','wuji-regrasp-fresh-ppo-v6','wuji-regrasp-fresh-free-v7','wuji-regrasp-fresh-free-v8','wuji-regrasp-fresh-free-v9','wuji-regrasp-fresh-free-v10']
        self.pose_motion_observation=saved['format'] in ['wuji-regrasp-fresh-free-v8','wuji-regrasp-fresh-free-v9','wuji-regrasp-fresh-free-v10'];self.pose_motion=PoseMotion();self.free_motor=saved['format'] in ['wuji-regrasp-fresh-free-v7','wuji-regrasp-fresh-free-v8','wuji-regrasp-fresh-free-v9','wuji-regrasp-fresh-free-v10'];self.incremental=saved['format'] in ['wuji-regrasp-fresh-ppo-v3','wuji-regrasp-fresh-ppo-v6','wuji-regrasp-fresh-free-v7','wuji-regrasp-fresh-free-v8','wuji-regrasp-fresh-free-v9','wuji-regrasp-fresh-free-v10'];self.task_geometry=saved['format'] in ['wuji-regrasp-fresh-ppo-v6','wuji-regrasp-fresh-free-v7','wuji-regrasp-fresh-free-v8','wuji-regrasp-fresh-free-v9','wuji-regrasp-fresh-free-v10'];self.action_dim=27 if self.free_motor else 28
        expected='free-motor-hold-v8' if self.pose_motion_observation else 'free-motor-hold-v7' if self.free_motor else PAUSE_TIMING if self.incremental or saved['format'].endswith('v2') else LEGACY_TIMING
        self.timing=saved['config'].get('phase_semantics',expected)
        assert self.timing==expected,'Checkpoint format and timing semantics disagree'
        self.action_period=int(saved['config'].get('action_period_frames',5))
        self.episode_steps=int(saved['config'].get('episode_steps',240))
        assert self.action_period>0 and self.episode_steps>0
        if self.incremental:
            from scripts.train_wuji_fresh_regrasp import FreshRegraspActor
            from scripts.g2_contact_geometry import DigitGeometry
            self.geometry=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')
            self.low=np.r_[self.kin.lower,self.geometry.w.lower];self.high=np.r_[self.kin.upper,self.geometry.w.upper]
            self.pad_vertices=np.concatenate([v for v,_ in self.geometry.meshes['hand_r_thumb_pad_link']])
            self.slider_half=np.array([.007,.002,.032])/2
            self.actor=FreshRegraspActor(168 if self.task_geometry else 158,self.action_dim).cuda()
        else:self.actor=RegraspActor().cuda()
        self.actor.load_state_dict(saved['model']);self.actor.eval()
        self.span=np.asarray(saved['motor_span']);self.slew=np.asarray(saved['motor_slew']);self.offset=np.zeros(27)
        recipe=json.loads(Path(saved['config']['reference']).read_text())
        self.motor=np.asarray([r['arm_q']+r['hand_q'] for r in recipe['rows']])
        L=np.asarray(recipe['target_object_in_wrist']);self.goal=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_quat()]
        self.goal_q=np.asarray(recipe['target_hand_q']);self.tick=0;self.action=np.zeros(self.action_dim);self.correction=None;self.warmed=False;self.entry_dwell=0;self.entry_ready=False;self.slider_start=None
        self.affordance=None;self.affordance_cache=None;self.task_feature_cache=dict(path_error=.03,self_bad=False,eligible=False)
        self.workspace_query_distance_m=float(saved['config'].get('workspace_query_distance_m',.004));self.workspace_cadence_frames=int(saved['config'].get('workspace_cadence_frames',15))
        if saved['config'].get('functional_workspace'):
            from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
            self.affordance=FunctionalEntryAffordance()
        self.noise_tape=np.load(spec['action_noise']) if spec.get('action_noise') else None
        if self.noise_tape is not None:assert self.incremental and self.noise_tape.ndim==2 and self.noise_tape.shape[1]==self.action_dim
        self.stream=(self.output/'regrasp-policy-call.jsonl').open('w',buffering=1)
        (self.output/'regrasp-policy-source.json').write_text(json.dumps({'checkpoint':str(checkpoint),'sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'training_round':saved['round'],'phase_semantics':self.timing,'action_period_frames':self.action_period,
            'scope':'New transition actor only; retained pushing actor unchanged'},indent=2))

    def command(self,O,q,velocity,issued,contacts,body_names,object_velocity=None,slider=None,slider_velocity=None,relative_orientation_xyzw=None):
        incremental=getattr(self,'incremental',False)
        q=np.asarray(q);issued=np.asarray(issued)
        if getattr(self,'pose_motion_observation',False):object_velocity=self.pose_motion.update(np.r_[O[:3,3],Rotation.from_matrix(O[:3,:3]).as_quat()])
        if not self.warmed:
            self.warmed=True
            return issued[:7].copy(),issued[7:].copy()
        if self.correction is None:
            self.correction=(issued-self.motor[0]) if incremental else self.kin.forward(q[:7])@np.linalg.inv(self.kin.forward(self.motor[0,:7]))
        W=self.kin.forward(q[:7]);L=np.linalg.inv(W)@O;rel=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_quat()]
        # Preserve the actual raw quaternion product used by training.
        # Matrix->quaternion reconstruction can choose the opposite sign.
        if relative_orientation_xyzw is not None:rel[3:]=np.asarray(relative_orientation_xyzw)
        goal=self.goal.copy()
        if np.dot(goal[3:],rel[3:])<0:goal[3:]*=-1
        c=np.array([min(3.,sum(np.linalg.norm(contacts[i]) for i,n in enumerate(body_names) if '_'+f+'_' in n))/3. for f in ['thumb','index','middle','ring','pinky']])
        obs=np.r_[q,np.asarray(velocity)*.05,issued-q,self.offset,rel[:3]*10,rel[3:],goal[:3]*10,goal[3:],self.goal_q,self.phase/(len(self.motor)-1),self.tick/self.episode_steps,c]
        assert obs.shape==(149,)
        if incremental:
            assert object_velocity is not None and slider is not None and slider_velocity is not None
            g=self.geometry.knife_geometry;S=O.copy();S[:3,3]=O[:3,3]+O[:3,:3]@(g.joint_xyz+g.joint_r@g.axis*slider);S[:3,:3]=O[:3,:3]@g.joint_r
            P=W@self.geometry.w.forward(q[7:])['hand_r_thumb_pad_link'];world=self.pad_vertices@P[:3,:3].T+P[:3,3];local=(world-S[:3,3])@S[:3,:3]
            distance=np.linalg.norm(np.maximum(abs(local)-self.slider_half,0),axis=-1).min();obs=np.r_[obs,np.asarray(object_velocity)[:3],np.asarray(object_velocity)[3:]*.05,slider*10,slider_velocity*.2,distance*100]
            assert obs.shape==(158,)
            if self.slider_start is None:self.slider_start=float(slider)
            clearance=float(O[2,3]-.75-abs(O[2,2])*.072-abs(O[2,1])*.006-abs(O[2,0])*.0095)
            reserve=float(np.minimum(q[23:]-self.low[23:],self.high[23:]-q[23:]).min())
            entry=(clearance>.025 and distance<.0015 and reserve>.075 and np.linalg.norm(object_velocity[:3])<.08 and np.linalg.norm(object_velocity[3:])<.8 and abs(slider-self.slider_start)<.002)
            if getattr(self,'affordance',None) is not None:
                radius=getattr(self,'workspace_query_distance_m',.004);cadence=getattr(self,'workspace_cadence_frames',15)
                if self.tick%15==0 and getattr(self,'task_geometry',False) and not (distance<radius and self.tick%cadence==0):
                    self.task_feature_cache['self_bad']=bool(self.affordance.H.inspect(q[7:]))
                    if distance>=radius:self.task_feature_cache['eligible']=False;self.affordance_cache=None
                if self.tick%cadence==0 and distance<radius:
                    self.affordance_cache=self.affordance.assess(q.astype(float),O,slider)
                    self.task_feature_cache=dict(path_error=min(.04,self.affordance_cache['full30mm_FK_error_m']),self_bad=bool(self.affordance_cache['self_intersections']),eligible=self.affordance_cache['reference_eligible'])
                entry=entry and self.affordance_cache is not None and self.affordance_cache['reference_eligible'] and not self.task_feature_cache['self_bad']
            if getattr(self,'task_geometry',False):
                body_local=(world-O[:3,3])@O[:3,:3];weights=np.exp(-(body_local[:,1]-body_local[:,1].min())/.0002);foot=weights@body_local/weights.sum();center_z=-.026+slider;clamped=np.clip(foot,[-.0035,.006,center_z-.016],[.0035,.006,center_z-.008]);delta=foot-clamped;cache=self.task_feature_cache
                extra=np.r_[delta*100,np.linalg.norm(delta)*100,cache['path_error']*100,float(cache['self_bad']),(slider-self.slider_start)*100,np.linalg.norm(object_velocity[:3])*5,np.linalg.norm(object_velocity[3:]),float(cache['eligible'])];assert extra.shape==(10,);obs=np.r_[obs,extra];assert obs.shape==(168,)
            self.entry_dwell=self.entry_dwell+1 if entry else 0
            self.entry_ready=self.entry_dwell>=int(self.spec.get('entry_probe_dwell_frames',30))
            if self.entry_ready and self.spec.get('state_ready_takeover'):
                if getattr(self,'affordance',None) is not None:
                    current=self.affordance.assess(q.astype(float),O,slider)
                    if not current['reference_eligible']:
                        self.entry_ready=False;self.entry_dwell=0
            if self.entry_ready and self.spec.get('state_ready_takeover'):
                self.stream.write(json.dumps({'tick':self.tick,'phase':self.phase,'entry_ready':True,'dwell_frames':self.entry_dwell,'cap_distance_m':float(distance),'clearance_m':clearance,'scope':'Measured functional proxy invokes original B to test actualcapacity, not acceptance'})+'\n')
                return issued[:7].copy(),issued[7:].copy()
        if self.tick%self.action_period==0:
            with torch.no_grad():self.action=self.actor(torch.as_tensor(obs,dtype=torch.float32,device='cuda').reshape(1,-1))[0].mean[0].cpu().numpy()
            if self.noise_tape is not None:
                index=self.tick//self.action_period
                if index>=len(self.noise_tape):raise RuntimeError('Frozencandidate noise exhausted before verifiedB handoff; reject rather than inventcontinuation')
                self.action+=self.noise_tape[index]
            self.action=self.action.clip(-1,1)
        if incremental:self.offset=np.clip(self.offset+self.action[:27]*self.slew,-self.span,self.span)
        else:self.offset+=np.clip(self.action[:27]*self.span-self.offset,-self.slew,self.slew)
        advance=0. if getattr(self,'free_motor',False) else float(phase_increment(np.asarray(self.action[27]),self.timing))
        self.phase=min(len(self.motor)-1.0001,self.phase+advance);i=int(self.phase);a=self.phase-i
        target=self.motor[i]*(1-a)+self.motor[i+1]*a
        # Arm coordinate adaptation changes motor commands only, preserving
        # this episode's actual object state and all velocities/history.
        if incremental:
            guide=target+self.correction;target=np.clip(issued+np.clip(guide+self.offset-issued,-self.slew,self.slew),self.low,self.high);self.offset=target-guide;ik={'scope':'All27 jointanchor motor commands, original bounds and totalslew; no IK follower'}
        else:
            adapted,ik=self.kin.solve_near(self.correction@self.kin.forward(target[:7]),q[:7],max_step=.12)
            target[:7]=adapted;target+=self.offset
        self.stream.write(json.dumps({'tick':self.tick,'phase':self.phase,'phase_increment':advance,'phase_semantics':self.timing,
                                     'action':self.action.tolist(),'object_in_wrist':L.tolist(),'ik':ik})+'\n')
        self.tick+=1
        return target[:7],target[7:]
