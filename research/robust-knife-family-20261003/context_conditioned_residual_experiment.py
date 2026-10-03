"""Separate development hypothesis: cached measured closing-context thickness.

Invoke --mode train|check --conditioning estimated|constant followed by the
unchanged trainer/checker arguments. Original frozen runtime remains intact.
No current object/slider/contact/material/assetID enters the context channel.
"""
import argparse,pathlib,json,hashlib,sys
from scripts.g2_continuous_scene import G2ContinuousScene as OriginalScene
from scripts.g2_batched_r800 import original_to_acquisition_observations,align_quaternion_hemisphere
from isaacgymenvs.utils.torch_jit_utils import quat_apply
import torch,numpy as np
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003'
HEAD=D/'closing-hold-identifiability-8s-v1/ridge-models.npz'
CONTEXT_OUTPUT=None

def context_input(scene,q,gravity):
 b=scene.bridge;norm=b.normalized(q);fk=b.fk(q);initial=torch.cat([norm,scene.cal_object,scene.cal_slider,fk,b.geometry],-1)
 pol=torch.cat([initial,norm,b.last_action,scene.goal[:,None],fk],-1);priv=q.new_zeros((scene.n,21));pol,priv=original_to_acquisition_observations(pol,priv);pol,priv=align_quaternion_hemisphere(pol,priv,b.single.reference)
 public134=torch.cat([pol,b.known.observed_targets(),gravity],-1)
 h=b.history[:,:,:20];return torch.cat([public134,h.mean(1),h.std(1,unbiased=False),h[:,-1]-h[:,0]],-1)

def install(conditioning):
 head=np.load(HEAD);weight=head['public134_history_stats_weight'];mean=head['public134_history_stats_input_mean'];std=head['public134_history_stats_input_std'];label_mean=head['label_mean_mm'];label_std=head['label_std_mm'];assert weight.shape==(194,5)
 class ContextScene(OriginalScene):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs);assert self.public_dim==154 and self.takeover_frame==480
   self.public_dim=155;self.context=torch.zeros((self.n,1),device=self.device);self.context_captured=torch.zeros(self.n,device=self.device,dtype=torch.bool);self.context_weight=torch.tensor(weight[:,1],device=self.device,dtype=torch.float32);self.context_mean=torch.tensor(mean,device=self.device,dtype=torch.float32);self.context_std=torch.tensor(std,device=self.device,dtype=torch.float32);self.context_label_mean=float(label_mean[1]);self.context_label_std=float(label_std[1]);self.context_records=[]
   if CONTEXT_OUTPUT is not None:
    np.savez_compressed(CONTEXT_OUTPUT/'context-initial-snapshot.npz',**{k:v.cpu().numpy().copy() for k,v in {'root':self.root,'dof':self.dof,'materials':self.material_tensor,'observation_bias':self.observation_bias,'delay':self.delay,'cal_object':self.cal_object,'cal_slider':self.cal_slider,'load_amplitude':self.load_amplitude,'detent_amplitude':self.detent_amplitude,'load_phase':self.load_phase}.items()})
  def close(self):
   if CONTEXT_OUTPUT is not None:(CONTEXT_OUTPUT/'closing-context-captures.json').write_text(json.dumps({'captures':self.context_records,'conditioning':conditioning,'scope':'Actual8s pre-policy measuredcontext capture; no runtimegeometry truth andnopickupsuccessfilter'},indent=2))
   super().close()
  def reset(self,ids):
   super().reset(ids)
   if hasattr(self,'context_captured'):self.context_captured[ids]=False;self.context[ids]=0
  def features(self):
   self.public_dim=154
   try:public,critic=super().features()
   finally:self.public_dim=155
   ready=(self.age==240)&~self.context_captured
   if ready.any():
    assert bool((self.bridge.history_count[ready]>=50).all());x=context_input(self,self._measurement,public[:,-3:]);thickness=((x-self.context_mean)/self.context_std)@self.context_weight*self.context_label_std+self.context_label_mean
    self.context[ready,0]=((thickness[ready]-12.)/2).clamp(-1.5,1.5) if conditioning=='estimated' else 0.
    self.context_captured[ready]=True
    self.context_records.append({'capture_count':int(ready.sum()),'age_control_frames':240,'estimated_T_mean_mm':float(thickness[ready].mean()),'estimated_T_min_mm':float(thickness[ready].min()),'estimated_T_max_mm':float(thickness[ready].max()),'conditioning':conditioning,'scope':'Predictions fromactualmeasured50q andknowncalibration/issuedtargets, labelsnotruntimeinput; allcaseskept'})
   return torch.cat([public,self.context],-1),torch.cat([critic,self.context],-1)
 import scripts.g2_continuous_scene as scene_module
 scene_module.G2ContinuousScene=ContextScene
 return ContextScene

def main():
 global CONTEXT_OUTPUT
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--mode',choices=['train','check'],required=True);p.add_argument('--conditioning',choices=['estimated','constant'],required=True);a,remaining=p.parse_known_args();assert HEAD.is_file();CONTEXT_OUTPUT=pathlib.Path(remaining[remaining.index('--output')+1]);install(a.conditioning);sys.argv=[sys.argv[0],*remaining]
 output=pathlib.Path(remaining[remaining.index('--output')+1]);spec={'conditioning':a.conditioning,'head_path':str(HEAD.relative_to(R)),'head_sha256':hashlib.sha256(HEAD.read_bytes()).hexdigest(),'public_dim':155,'critic_dim':182,'actor_layout':'Original154 +cachedclosingnormalizedTestimate1','critic_layout':'Original181 +samecachedcontext1','capture_age_frames':240,'capture_policy_active':False,'fit_scope':'Frozen ridge10 on409 trainingfamily bodylabels;103 geometry-supervision heldout. Labelsneveractorinput. Earlyactualcontext before16s takeover.', 'runtime_inputs':'50actualmeasurednormalizedq, currentmeasuredq/FK, knownnominalgeometry/calibration, knownissuedtargets/previousactions, measuredarmFKgravity; no object/slider/contact/material/assetID','prototype_scope':'Separatepaireddevelopmentonly, not originalP50/nativeG2R800Policy/hardware or332primaryindependent candidate'}
 if a.mode=='train':
  import scripts.train_wuji_robust_residual as runner
 else:
  import scripts.check_g2_continuous_scene as runner
  runner.G2ContinuousScene=__import__('scripts.g2_continuous_scene',fromlist=['G2ContinuousScene']).G2ContinuousScene
 runner.main();(output/'context-spec.json').write_text(json.dumps(spec,indent=2))
 if a.mode=='train':
  for path in output.glob('update_*.pth'):
   saved=torch.load(path,map_location='cpu');saved['context_conditioning_spec']=spec;saved['actor_inputs']+=';cachedclosingmeasuredTestimate1';saved['critic_inputs']='Original181 pluscachedmeasuredcontext1';saved['format']='wuji-r800-residual-context-development-v1';torch.save(saved,path);path.with_suffix('.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'\n')
if __name__=='__main__':main()
