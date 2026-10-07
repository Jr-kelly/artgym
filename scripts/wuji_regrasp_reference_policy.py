"""Native controller for the contact-changing short policy, not the push actor."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.train_wuji_regrasp import RegraspActor
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_regrasp_contract import phase_increment, PAUSE_TIMING, LEGACY_TIMING

class RegraspReferencePolicy:
    def __init__(self,spec,output):
        self.spec=spec;self.output=Path(output);self.kin=G2Kinematics();self.phase=0.
        checkpoint=Path(spec['checkpoint']);saved=torch.load(checkpoint,map_location='cpu')
        assert saved['format'] in ['wuji-regrasp-reference-ppo-v1','wuji-regrasp-reference-ppo-v2']
        expected=PAUSE_TIMING if saved['format'].endswith('v2') else LEGACY_TIMING
        self.timing=saved['config'].get('phase_semantics',expected)
        assert self.timing==expected,'Checkpoint format and timing semantics disagree'
        self.action_period=int(saved['config'].get('action_period_frames',5))
        self.episode_steps=int(saved['config'].get('episode_steps',240))
        assert self.action_period>0 and self.episode_steps>0
        self.actor=RegraspActor().cuda();self.actor.load_state_dict(saved['model']);self.actor.eval()
        self.span=np.asarray(saved['motor_span']);self.slew=np.asarray(saved['motor_slew']);self.offset=np.zeros(27)
        recipe=json.loads(Path(saved['config']['reference']).read_text())
        self.motor=np.asarray([r['arm_q']+r['hand_q'] for r in recipe['rows']])
        L=np.asarray(recipe['target_object_in_wrist']);self.goal=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_quat()]
        self.goal_q=np.asarray(recipe['target_hand_q']);self.tick=0;self.action=np.zeros(28);self.correction=None;self.warmed=False
        self.stream=(self.output/'regrasp-policy-call.jsonl').open('w',buffering=1)
        (self.output/'regrasp-policy-source.json').write_text(json.dumps({'checkpoint':str(checkpoint),'sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'training_round':saved['round'],'phase_semantics':self.timing,'action_period_frames':self.action_period,
            'scope':'New transition actor only; retained pushing actor unchanged'},indent=2))

    def command(self,O,q,velocity,issued,contacts,body_names):
        q=np.asarray(q);issued=np.asarray(issued)
        if not self.warmed:
            self.warmed=True
            return issued[:7].copy(),issued[7:].copy()
        if self.correction is None:
            self.correction=self.kin.forward(q[:7])@np.linalg.inv(self.kin.forward(self.motor[0,:7]))
        W=self.kin.forward(q[:7]);L=np.linalg.inv(W)@O;rel=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_quat()]
        goal=self.goal.copy()
        if np.dot(goal[3:],rel[3:])<0:goal[3:]*=-1
        c=np.array([min(3.,sum(np.linalg.norm(contacts[i]) for i,n in enumerate(body_names) if '_'+f+'_' in n))/3. for f in ['thumb','index','middle','ring','pinky']])
        obs=np.r_[q,np.asarray(velocity)*.05,issued-q,self.offset,rel[:3]*10,rel[3:],goal[:3]*10,goal[3:],self.goal_q,self.phase/(len(self.motor)-1),self.tick/self.episode_steps,c]
        assert obs.shape==(149,)
        if self.tick%self.action_period==0:
            with torch.no_grad():self.action=self.actor(torch.as_tensor(obs,dtype=torch.float32,device='cuda').reshape(1,-1))[0].mean[0].cpu().numpy().clip(-1,1)
        self.offset+=np.clip(self.action[:27]*self.span-self.offset,-self.slew,self.slew)
        advance=float(phase_increment(np.asarray(self.action[27]),self.timing))
        self.phase=min(len(self.motor)-1.0001,self.phase+advance);i=int(self.phase);a=self.phase-i
        target=self.motor[i]*(1-a)+self.motor[i+1]*a
        # Arm coordinate adaptation changes motor commands only, preserving
        # this episode's actual object state and all velocities/history.
        adapted,ik=self.kin.solve_near(self.correction@self.kin.forward(target[:7]),q[:7],max_step=.12)
        target[:7]=adapted;target+=self.offset
        self.stream.write(json.dumps({'tick':self.tick,'phase':self.phase,'phase_increment':advance,'phase_semantics':self.timing,
                                     'action':self.action.tolist(),'object_in_wrist':L.tolist(),'ik':ik})+'\n')
        self.tick+=1
        return target[:7],target[7:]
