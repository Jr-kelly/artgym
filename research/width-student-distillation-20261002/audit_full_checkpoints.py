"""CPU-only audit of every saved encoder, actual Adam, RNG and sampler counts."""
import argparse,datetime,hashlib,json
import torch
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_contract import sha

def audit(pair,output):
    rows=[]
    for arm in ['C','G']:
        for step in [52000,52800,54400]:
            path=R/'runs/width-student-distillation-20261002'/(arm+str(pair)+'-window1-h200-17314')/('step_%06d.pth'%step)
            j=torch.load(path,map_location='cpu')
            assert json.loads(path.with_suffix('.ready.json').read_text())['sha256']==sha(path)
            pg=j['optimizer']['param_groups']
            assert len(pg)==1 and pg[0]['lr']==.0003 and pg[0]['betas']==(.9,.999) and pg[0]['eps']==1e-8 and pg[0]['weight_decay']==0
            steps=[int(o['step'].item()) for o in j['optimizer']['state'].values()]
            assert min(steps)==max(steps)==step
            w=j['width_sampler'];trans=sum(sum(row) for row in w['transition_counts'])
            assert trans==(step-51200)*1024 and not w['metadata_in_policy']
            assert j['interactions']==step*1024 and j['teacher_sha256']=='2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8'
            assert j['frozen_hash']=='f8775c12963a51e1adc225b1fdd107df71eb0bc6b7e1291845ad410693361232'
            assert j['teacher_encoder_hash']=='0576893b4f285bfc57b052b0daa11f4810cb017dd44c906f31120ae216c25198'
            assert {'python','numpy','torch','cuda'}.issubset(j['rng'])
            h=hashlib.sha256()
            for k,v in sorted(j['student_encoder'].items()):h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
            rows.append(dict(arm=arm,pair=pair,step=step,path=str(path.relative_to(R)),sha256=sha(path),encoder_sha256=h.hexdigest(),adam_step_min=min(steps),adam_step_max=max(steps),optimizer_param_groups=pg,added_updates=step-51200,added_transitions=trans,group_source_transition_counts=w['transition_counts'],group_source_reset_counts=w['reset_counts'],sampler_manifest_sha256=w['manifest_sha256'],frozen_actor_normalizer_sha256=j['frozen_hash'],teacher_encoder_sha256=j['teacher_encoder_hash'],controller_mode=j['controller_mode'],kind=j['kind'],optimization_seed=j['args']['fresh_optimization_seed']))
    assert not output.exists()
    output.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pair=pair,checkpoints=rows,formal_updates=6400,formal_transitions=6553600,per_arm=3200,resets_note='Sampler reset counters include256 initial slots; aggregate resets exclude those. Geometry groups are logical inC, allphysicalbaseline.',resume_scope='Encoder/Adam/RNG restored; new experiment resets simulator. No bitwise PhysX continuation claim.'),indent=2)+'\n')
    record('all_six_formal_pair_checkpoints_audited',evidence=str(output.relative_to(R)),pair=pair,next='Preserve all full checkpoint states and actual sampler counts in release')
    print(json.dumps(dict(pair=pair,checkpoints=len(rows),formal_updates=6400,formal_transitions=6553600)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pair',type=int,choices=[1,2],required=True);p.add_argument('--output',required=True);a=p.parse_args();audit(a.pair,(R/a.output).resolve())
