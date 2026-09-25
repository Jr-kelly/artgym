"""Independently rescore all ten final100-repeat cycle matrices."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists()
    rows=[]
    for arm in ['teacher','student']:
        d=json.loads((args.run/arm/'result.json').read_text());assert d['status']=='completed'
        success=total=0;groups=[]
        for name in ['030','031','032','033','034']:
            path=args.run/arm/(name+'.json');r=json.loads(path.read_text())
            cycles=np.array(r['consecutive_success_cycles_trials'])
            assert cycles.shape==(100,r['num_grasps']) and np.isfinite(cycles).all()
            assert (cycles>=0).all() and np.equal(cycles,cycles.astype(int)).all()
            s=int((cycles>=1).sum());n=cycles.size
            assert s==r['successful_trials'] and n==r['total_trials']
            if arm=='student':
                a=r['student_audit'];assert a['status']=='passed' and a['weights_unchanged']
                assert a['completed_updates']==1000 and a['checks']['actual_actions']==a['checks']['restricted_inputs']
                assert a['checks']['privileged_invariance']>0
            groups.append(dict(instance=name,success=s,total=n,mean_cycles=float(cycles.mean()),
                covered_grasps=int((cycles.max(0)>=1).sum()),num_grasps=r['num_grasps'],report_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            success+=s;total+=n
        assert total==28700==d['total_trials'] and success==d['successful_trials']
        rows.append(dict(arm=arm,success=success,total=total,execution_success_rate=success/total,groups=groups))
    args.output.write_text(json.dumps(dict(status='verified',rows=rows,all10_cycle_matrices_rescored=True,
        scope='FixedteacherCP2100 vsfinalstudentCP1000. Fivepreviouslyobservedgeometries,287grasps x100newrandomizedepisodes,10mmarrivalcycles. CrossGPU/onefittingseed;notWuji2mmtimedcriterion orfull2Bteacherpaperreplication.'),indent=2)+'\n')
    print(json.dumps(rows))


if __name__=='__main__':
    main()
