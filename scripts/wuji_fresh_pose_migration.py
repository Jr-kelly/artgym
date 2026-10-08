"""Explicit v7 to v8: same 168-input/27-output weights and Adam.

Only actual-pose motion sensing and physically verified motor prefix change.
Equal-output checks use identical synthetic inputs, not physical equivalence.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import isaacgym
import torch
from scripts.train_wuji_fresh_regrasp import FreshRegraspActor
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--fail-on-self-contact',action='store_true');p.add_argument('--functional-contact-reward',action='store_true');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix-motor-trace',type=Path,required=True);p.add_argument('--motor-preamble',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
 old=torch.load(a.source,map_location='cpu');assert old['format']==('wuji-regrasp-fresh-free-v9' if a.functional_contact_reward else 'wuji-regrasp-fresh-free-v8' if a.fail_on_self_contact else 'wuji-regrasp-fresh-free-v7') and 'optimizer' in old;s=copy.deepcopy(old)
 s['format']='wuji-regrasp-fresh-free-v8';s['config'].update(pose_motion_observation=True,object_motion_sensor='pose-difference-world-30hz-v1',phase_semantics='free-motor-hold-v8',motor_action_mode='free-motor-v8-pose',reward_version='free-workspace-closedslider-allhand-v8-pose',prefix_trace=str(a.prefix_motor_trace),prefix_sha256=hashlib.sha256(a.prefix_motor_trace.read_bytes()).hexdigest(),motor_preamble=str(a.motor_preamble))
 if a.functional_contact_reward:s['format']='wuji-regrasp-fresh-free-v10';s['config'].update(fail_on_self_contact=True,functional_contact_reward=True,reward_version='free-workspace-closedslider-allhand-v10-functional-contact')
 elif a.fail_on_self_contact:s['format']='wuji-regrasp-fresh-free-v9';s['config'].update(fail_on_self_contact=True,reward_version='free-workspace-closedslider-allhand-v9-selfterminal')
 before=FreshRegraspActor(168,27).eval();before.load_state_dict(old['model']);after=FreshRegraspActor(168,27).eval();after.load_state_dict(s['model']);torch.manual_seed(835);x=torch.randn(512,168);checks={}
 for device in ['cpu','cuda']:
  before=before.to(device);after=after.to(device)
  with torch.no_grad():od,ov=before(x.to(device));nd,nv=after(x.to(device))
  checks[device]=dict(actor_equal=bool(torch.equal(od.mean,nd.mean)),critic_equal=bool(torch.equal(ov,nv)),std_equal=bool(torch.equal(od.scale,nd.scale)));assert all(checks[device].values())
 assert s['motor_span']==old['motor_span'] and s['motor_slew']==old['motor_slew']
 opt=torch.optim.Adam(after.parameters(),lr=3e-4);opt.load_state_dict(s['optimizer'])
 for parameter,state in opt.state.items():assert state['exp_avg'].shape==parameter.shape and state['exp_avg_sq'].shape==parameter.shape
 audit=dict(parent=str(a.source),parent_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),checks=checks,unchanged='All weights/Adam/168 dimensions/27 incremental actions/original spans/slew/PD/physics/B',scope='Explicit operatingcontact-foot/reserve reward alignment afteractual850Bpreparation failure; no NN/control/input/physics/B changes' if a.functional_contact_reward else 'Explicit self-geometric failure at existing15frame actualH checks; no weights/Adam/motion/control/physics/B changes' if a.fail_on_self_contact else __doc__);s['migration']=audit;torch.save(s,a.output/'checkpoint.pth');audit['checkpoint_sha256']=hashlib.sha256((a.output/'checkpoint.pth').read_bytes()).hexdigest();(a.output/'audit.json').write_text(json.dumps(audit,indent=2));record('fresh_actual_pose_motion_v8_migration_verified',[str(a.output/'audit.json')],audit,next_step='Actual fresh stable motor prefix -> free27 learning -> original complete B at measured reachable safe entry; first B result ends batch');print(json.dumps(audit))
if __name__=='__main__':main()
