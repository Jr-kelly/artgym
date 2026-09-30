"""Index actual archived checkpoint hashes and CPU-readable continuation metadata."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import torch

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];entries={};archives=[]
    for receipt in sorted((root/'delivery/artmanip-recovery-20260930').glob('*.receipt.json')):
        item=json.loads(receipt.read_text());path=root/item['archive']
        assert sha(path)==item['sha256']
        with tarfile.open(path) as tf:
            members=[m for m in tf.getmembers() if m.name.startswith('release-manifests/') and m.name.endswith('.json')]
            assert len(members)==1;manifest=json.load(tf.extractfile(members[0]))
        archives.append(dict(archive=item['archive'],sha256=item['sha256']))
        for f in manifest['files']:
            if not f['path'].endswith('.pth'):continue
            key=(f['path'],f['sha256'])
            if key not in entries:
                local=root/f['path'];assert sha(local)==f['sha256']
                state=torch.load(local,map_location='cpu');state=state[0] if 0 in state else state
                bc='bc_optimizer' in state
                optimizer=state.get('bc_optimizer' if bc else 'optimizer',{})
                steps=sorted(set(int(x['step']) for x in optimizer.get('state',{}).values() if 'step' in x))
                entries[key]=dict(path=f['path'],sha256=f['sha256'],size=f['size'],kind='offline_BC' if bc else 'RL_or_parent_expert',epoch=state.get('bc_epoch' if bc else 'epoch'),optimizer_updates=state.get('bc_updates' if bc else 'recovery_optimizer_updates'),adam_steps=steps,environment_interactions=0 if bc else state.get('frame'),has_normalizer=bool('running_mean_std' in state or any('running_mean_std' in k for k in state.get('model',{}))),rng_keys=sorted(k for k in state if k.startswith('bc_') and 'rng' in k) if bc else sorted(state.get('recovery_rng',{})),archives=[])
            entries[key]['archives'].append(item['archive'])
    result=dict(scope='Archived checkpoint inventory, actual archive and local-file SHA256 checks plus CPU deserialization. Historical PPO parent metadata is not evidence of this round training. PhysX is not serialized. No claim of policy success.',weights=list(entries.values()),archives=archives)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(weights=len(entries),archives=len(archives),output=str(a.output))))

if __name__=='__main__':main()
