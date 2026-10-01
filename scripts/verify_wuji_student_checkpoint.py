"""CPU restore audit: saved optimizer counters/RNG and equivalent next Adam update."""
import argparse,copy,hashlib,json
from pathlib import Path
import isaacgym
import torch
from scripts.wuji_student_interface import build_encoder,tensor_hash

def main():
 p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 saved=torch.load(a.checkpoint,map_location='cpu');assert saved['format']=='wuji-unified-student-v1'
 assert a.checkpoint.with_suffix('.sha256').read_text().strip()==hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()
 steps=saved['optimizer_steps'];models=[];opts=[]
 for _ in range(2):
  m=build_encoder(saved['kind']);m.load_state_dict(saved['student_encoder']);m.eval();models.append(m)
  opt=torch.optim.Adam(m.parameters(),lr=saved['args']['lr']);opt.load_state_dict(copy.deepcopy(saved['optimizer']));opts.append(opt)
  assert set(int(s['step']) for s in opt.state.values())=={steps}
 assert tensor_hash(models[0].state_dict())==tensor_hash(saved['student_encoder'])
 torch.set_num_threads(2);torch.manual_seed(61111)
 x=torch.randn(4,getattr(models[0],'input_dim',2055));label=torch.randn(4,16)
 losses=[]
 for model,opt in zip(models,opts):
  opt.zero_grad();loss=((model(x)-label)**2).mean();loss.backward();opt.step();losses.append(float(loss))
 assert tensor_hash(models[0].state_dict())==tensor_hash(models[1].state_dict())
 assert set(int(s['step']) for s in opts[0].state.values())=={steps+1}
 r=dict(checkpoint=str(a.checkpoint),sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),saved_steps=steps,next_steps=steps+1,restored_next_update_identical=True,has_rng=list(saved['rng']),frozen_hash=saved['frozen_hash'],scope='CPU restoration of encoder/Adam/RNG payload; physics resumes with new declared episodes, not serialized PhysX')
 a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
