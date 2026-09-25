"""Rescore the complete Sharpa student cycle matrices and check inference audits."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--update',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1];folder=root/'runs/sharpa_student_upstream2100_seed69_v3/evaluation'/f'cp{args.update:04d}'
    summary=json.loads((folder/'result.json').read_text());assert summary['status']=='completed' and summary['update']==args.update
    groups=[];reports={};total_actions=0
    for name in ['030','031','032','033','034']:
        path=folder/(name+'.json');d=json.loads(path.read_text());audit=d['student_audit']
        assert audit['status']=='passed' and audit['weights_unchanged'] and audit['completed_updates']==args.update
        assert audit['student_artifact_sha256']==summary['student_sha256']
        checks=audit['checks'];assert checks['actual_actions']==checks['restricted_inputs'] and checks['privileged_invariance']>0
        matrix=d['consecutive_success_cycles_trials'];assert len(matrix)==10 and all(len(row)==d['num_grasps'] for row in matrix)
        values=[v for row in matrix for v in row]
        assert all(math.isfinite(v) and v>=0 and v==int(v) for v in values)
        success=sum(v>=1 for v in values);assert success==d['successful_trials'] and len(values)==d['total_trials']
        assert abs(success/len(values)-d['execution_success_rate'])<1e-12
        assert checks['actual_actions']<=len(values)*1200
        total_actions+=checks['actual_actions']
        groups.append(dict(instance=name,success=success,trials=len(values),mean_cycles=sum(values)/len(values),
            covered_grasps=sum(max(row[i] for row in matrix)>=1 for i in range(d['num_grasps'])),
            total_grasps=d['num_grasps'],actual_actions=checks['actual_actions'],
            report_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        reports[name]=d
    assert sum(g['trials'] for g in groups)==summary['total_trials']==2870
    assert sum(g['success'] for g in groups)==summary['successful_trials']
    result=dict(update=args.update,successful_trials=summary['successful_trials'],total_trials=2870,
        execution_success_rate=summary['successful_trials']/2870,groups=groups,actual_actions=total_actions,
        all_cycle_matrices_rescored=True,restricted_input_and_weights_verified=True,original_reports=reports,
        student_sha256=summary['student_sha256'],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope=f'Frozen studentCP{args.update} using50x44+57proprioceptivehistory/initialinputs. Fiveheldoutgeometries,287graspsx10,original10mmonecyclecriterion. Existingdevelopmentonceobserved;notWuji2mmfixedclockorhardware. '+('Final1000-update checkpoint.' if args.update==1000 else 'Intermediate checkpoint.'))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='original_reports'}))


if __name__=='__main__':main()
