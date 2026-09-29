"""Rebase input normalization with first-layer affine compensation.

Exact for observations unclipped under both normalizers. Deliberately removes
old out-of-domain clipping; this is a method change, not exact policy copying.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import torch

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--policy',type=Path,required=True);p.add_argument('--normalizer',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 def read(path):
  c=torch.load(path,map_location='cpu');return c[0] if 0 in c else c
 c=copy.deepcopy(read(a.policy));s=c['model'];n=read(a.normalizer)['model'];prefix='running_mean_std.'
 oldm=s[prefix+'running_mean'].double();olds=(s[prefix+'running_var'].double()+1e-5).sqrt();newm=n[prefix+'running_mean'].double();news=(n[prefix+'running_var'].double()+1e-5).sqrt()
 scale=news/olds;shift=(newm-oldm)/olds;checks=[]
 def adjust(wkey,bkey,indices,columns):
  w=s[wkey].double();b=s[bkey].double();idx=torch.tensor(indices);cols=torch.tensor(columns);old=w[:,cols].clone();b=b+old@shift[idx];w[:,cols]=old*scale[idx][None,:]
  # Verify the exact affine algebra before casting; clipping is not part of this identity.
  x=torch.linspace(-1,1,steps=len(indices),dtype=torch.float64);expected=old@(scale[idx]*x+shift[idx])+s[bkey].double();actual=w[:,cols]@x+b
  error=float((expected-actual).abs().max());assert error<1e-9
  s[wkey]=w.to(s[wkey]);s[bkey]=b.to(s[bkey]);checks.append(dict(weight=wkey,affine_identity_error=error))
 for name in ['priv_encoder','critic_priv_encoder']:
  adjust('a2c_network.'+name+'.0.weight','a2c_network.'+name+'.0.bias',list(range(111,132)),list(range(21)))
 adjust('a2c_network.a_rnn.rnn.weight_ih_l0','a2c_network.a_rnn.rnn.bias_ih_l0',list(range(111)),list(range(111)))
 adjust('a2c_network.c_rnn.rnn.weight_ih_l0','a2c_network.c_rnn.rnn.bias_ih_l0',list(range(111))+list(range(132,137)),list(range(116)))
 for key in ['running_mean','running_var','count']:s[prefix+key]=n[prefix+key].clone()
 c['running_mean_std']={k:s[prefix+k].clone() for k in ['running_mean','running_var','count']};c.pop('optimizer',None)
 receipt=dict(policy=str(a.policy),policy_sha256=sha(a.policy),normalizer=str(a.normalizer),normalizer_sha256=sha(a.normalizer),checks=checks,scope='Exact affine input compensation before clipping; formerly clipped inputs intentionally change. No source routing or added observations; actor/critic/encoders all compensated.')
 c['normalization_rebase']=receipt;a.output.parent.mkdir(parents=True,exist_ok=True);assert not a.output.exists();torch.save(c,a.output);receipt['output_sha256']=sha(a.output);a.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
