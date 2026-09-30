"""CPU audit of true paired continuation, normalization/critic freezing and RNG."""
import argparse,json,hashlib
from pathlib import Path
import torch,numpy as np

def load(p):
    x=torch.load(p,map_location='cpu');return x[0] if 0 in x else x

def equal_tree(a,b):
    if torch.is_tensor(a):return torch.is_tensor(b) and torch.equal(a,b)
    if isinstance(a,np.ndarray):return isinstance(b,np.ndarray) and np.array_equal(a,b)
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal_tree(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)):return isinstance(b,type(a)) and len(a)==len(b) and all(equal_tree(x,y) for x,y in zip(a,b))
    return a==b

def main():
    p=argparse.ArgumentParser();p.add_argument('--pair',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--epoch',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--parent-pair',type=Path);p.add_argument('--parent-epoch',type=int);p.add_argument('--arms',nargs='+',choices=['M','E'],default=['M','E']);a=p.parse_args()
    assert (a.parent_pair is None)==(a.parent_epoch is None)
    assert len(a.arms)==len(set(a.arms))
    base=load(a.initial);states={k:load(a.pair/k/f'epoch_{a.epoch:06d}.pth') for k in a.arms};rows=[]
    for k,s in states.items():
        checkpoint=a.pair/k/f'epoch_{a.epoch:06d}.pth'
        fixed=[name for name in base['model'] if not any('a2c_network.'+part in name for part in ['priv_encoder.','a_rnn.','a_layer_norm.','actor_mlp.','mu.'])]
        assert all(torch.equal(s['model'][name],base['model'][name]) for name in fixed)
        assert all(torch.isfinite(v).all() for v in s['model'].values())
        steps=sorted(set(int(v['step']) for v in s['bc_optimizer']['state'].values()));assert steps==[a.epoch*8]
        rows.append(dict(arm=k,epoch=s['bc_epoch'],updates=s['bc_updates'],adam_steps=steps,fixed_tensor_count=len(fixed),normalizer_critic_frozen=True,sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest()))
    paired=len(states)==2
    if paired:
        m,e=states['M'],states['E']
        assert equal_tree(m['bc_torch_rng'],e['bc_torch_rng']) and equal_tree(m['bc_cuda_rng'],e['bc_cuda_rng'])
        assert equal_tree(m['bc_numpy_rng'],e['bc_numpy_rng'])
    result=dict(rows=rows,paired=paired,same_end_rng=True if paired else None,passed=True,scope='Checkpoint integrity and optional paired optimizer/sequence random state, not a closed-loop score')
    if a.parent_pair:
        result['actual_resume']=[]
        for arm in a.arms:
            parent_path=a.parent_pair/arm/f'epoch_{a.parent_epoch:06d}.pth'
            start_path=a.pair/arm/f'epoch_{a.parent_epoch:06d}.pth'
            parent,start=load(parent_path),load(start_path)
            keys=['model','bc_optimizer','bc_torch_rng','bc_cuda_rng','bc_numpy_rng','bc_epoch','bc_updates']
            assert all(equal_tree(parent[k],start[k]) for k in keys),'Saved pre-update state differs from actual parent'
            first=json.loads((a.pair/arm/'training.jsonl').read_text().splitlines()[0])
            assert first['epoch']==a.parent_epoch+1
            assert first['updates']==parent['bc_updates']+len(first['batches'])
            result['actual_resume'].append(dict(arm=arm,parent_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),saved_start_sha256=hashlib.sha256(start_path.read_bytes()).hexdigest(),equal_fields=keys,first_epoch=first['epoch'],first_updates=first['updates']))
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
