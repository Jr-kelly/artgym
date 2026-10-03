"""Change only a registered reference; preserve learned model/Adam/RNG exactly."""
import argparse,hashlib,json
from pathlib import Path
import torch


def tensor_hash(state):
    h=hashlib.sha256()
    for key,value in sorted(state.items()):
        v=value.detach().cpu().contiguous();h.update(key.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.numpy().tobytes())
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    saved=torch.load(a.parent,map_location='cpu');assert saved['format']=='wuji-r800-residual-ppo-v1' and saved['action_base_mode']=='geometric';reference=json.loads(a.reference.read_text());assert reference['all_feasible'] and reference['motor_geometry_passed'] and reference['posture_preload']
    before=tensor_hash(saved['model']);saved['thumb_reference']=reference;saved['args']['thumb_reference']=a.reference
    adaptation=dict(parent_sha256=hashlib.sha256(a.parent.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),learned_model_tensor_sha256=before,new_updates=0,new_transitions=0,scope='Registered geometric/nominal impedance reference changed; exact existing learned actor/critic, optimizer and RNG retained. No new learning or measured force claim.')
    saved['controller_adaptation']=adaptation;a.output.parent.mkdir(parents=True,exist_ok=True);torch.save(saved,a.output);actual=torch.load(a.output,map_location='cpu');assert tensor_hash(actual['model'])==before
    receipt=dict(adaptation,checkpoint=str(a.output),checkpoint_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest());a.output.with_suffix('.sha256').write_text(receipt['checkpoint_sha256']+'\n');a.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))


if __name__=='__main__':main()
