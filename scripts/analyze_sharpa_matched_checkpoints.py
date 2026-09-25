"""Recompute matched Sharpa intermediate teacher scores from all cycle matrices."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--epoch',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1];rows=[];raw={}
    for condition,run in [('corrected','sharpa_reward_corrected_recover1500_exclusive_v1'),('upstream','sharpa_reward_upstream')]:
        path=root/'runs'/run/'evaluation/monitor'/f'epoch_{args.epoch:06d}'/'result.json'
        d=json.loads(path.read_text());assert d['status']=='completed' and d['epoch']==args.epoch
        assert set(d['instances'])=={'030','031','032','033','034'}
        groups=[]
        for name,instance in sorted(d['instances'].items()):
            matrix=instance['consecutive_success_cycles_trials']
            assert len(matrix)==10 and all(len(v)==instance['num_grasps'] for v in matrix)
            values=[v for row in matrix for v in row]
            assert all(math.isfinite(v) and v>=0 and v==int(v) for v in values)
            successful=sum(v>=1 for v in values)
            assert successful==instance['successful_trials'] and len(values)==instance['total_trials']
            groups.append(dict(instance=name,success=successful,trials=len(values),mean_cycles=sum(values)/len(values)))
        total=sum(g['trials'] for g in groups);success=sum(g['success'] for g in groups)
        assert total==d['total_trials']==2870 and success==d['successful_trials']
        assert abs(success/total-d['execution_success_rate'])<1e-12
        rows.append(dict(condition=condition,epoch=args.epoch,frames=d['frame'],successful_trials=success,
            total_trials=total,per_instance=groups,source=str(path.relative_to(root)),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),policy_sha256=d['policy_sha256']))
        raw[condition]=d
    assert rows[0]['frames']==rows[1]['frames']==args.epoch*320000
    args.output.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rows=rows,all_cycle_matrices_rescored=True,original_reports=raw,
        scope='Intermediate frozen privileged teachers. Five heldout geometries,287 grasps x10,original10mm at-least-one-cycle criterion. Matched epochs but single training seed, different hosts and corrected recovery history; not universal causal evidence, not Wuji strict student success or hardware.'),indent=2)+'\n')
    print(json.dumps(rows))


if __name__=='__main__':main()
