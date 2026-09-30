"""CPU audit of true paired continuation, normalization/critic freezing and RNG."""
import argparse,json,hashlib
from pathlib import Path
import torch,numpy as np

def load(p):
    x=torch.load(p,map_location='cpu');return x[0] if 0 in x else x

def main():
    p=argparse.ArgumentParser();p.add_argument('--pair',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--epoch',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base=load(a.initial);states={k:load(a.pair/k/f'epoch_{a.epoch:06d}.pth') for k in ['M','E']};rows=[]
    for k,s in states.items():
        checkpoint=a.pair/k/f'epoch_{a.epoch:06d}.pth'
        fixed=[name for name in base['model'] if not any('a2c_network.'+part in name for part in ['priv_encoder.','a_rnn.','a_layer_norm.','actor_mlp.','mu.'])]
        assert all(torch.equal(s['model'][name],base['model'][name]) for name in fixed)
        assert all(torch.isfinite(v).all() for v in s['model'].values())
        steps=sorted(set(int(v['step']) for v in s['bc_optimizer']['state'].values()));assert steps==[a.epoch*8]
        rows.append(dict(arm=k,epoch=s['bc_epoch'],updates=s['bc_updates'],adam_steps=steps,fixed_tensor_count=len(fixed),normalizer_critic_frozen=True,sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest()))
    m,e=states['M'],states['E']
    assert torch.equal(m['bc_torch_rng'],e['bc_torch_rng']) and all(torch.equal(x,y) for x,y in zip(m['bc_cuda_rng'],e['bc_cuda_rng']))
    assert all(np.array_equal(x,y) for x,y in zip(m['bc_numpy_rng'],e['bc_numpy_rng']))
    result=dict(rows=rows,same_end_rng=True,passed=True,scope='Checkpoint integrity and paired optimizer/sequence random state, not a closed-loop score')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
