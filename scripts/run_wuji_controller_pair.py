"""Gate both controller modes in physics before launching the bounded PPO pair."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pin',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    args=parser.parse_args()
    assert not (args.output/'status.json').exists()
    args.output.mkdir(parents=True,exist_ok=True)
    env=runtime_environment(dict(project=str(args.pin),python=sys.executable),3)
    record=dict(status='runtime_gates',started=now(),stages=[])
    atomic_json(args.output/'status.json',record)
    try:
        gates=[]
        for mode in ['false','true']:
            folder=args.output/mode
            folder.mkdir()
            command=[sys.executable,'-m','scripts.check_wuji_controller_actor_runtime','--checkpoint',str(args.checkpoint),
                     '--output',str(folder),'--enabled',mode,'--steps','600']
            with (folder/'worker.log').open('w') as log:
                child=subprocess.Popen(command,cwd=args.pin,env=env,stdout=log,stderr=subprocess.STDOUT)
                stage=dict(mode=mode,pid=child.pid,command=command,status='running')
                record['stages'].append(stage)
                atomic_json(args.output/'status.json',record)
                code=child.wait()
            stage.update(returncode=code,status='completed' if code==0 else 'failed')
            atomic_json(args.output/'status.json',record)
            assert code==0, mode
            gate=json.loads((folder/'report.json').read_text())
            assert gate['status']=='passed' and gate['checks']['transitions']==19200
            gates.append(gate)
        paired=dict(same_initial_physical_action_actor_trace=gates[0]['physical_action_actor_rnn_sha256']==gates[1]['physical_action_actor_rnn_sha256'],
                    total_physics_transitions=38400,
                    same_state_mode_checks=[gate['checks']['paired_mode_invariance'] for gate in gates],
                    passed=all(gate['checks']['paired_mode_invariance']==19200 for gate in gates),
                    interpretation='V1 cross-process bitwise mismatch retained. V2 compares both modes and reference actor at identical state/input/RNN inside each physical rollout; counterfactual does not enter physics.')
        atomic_json(args.output/'paired-gate.json',paired)
        assert paired['passed'], 'Same-state mode equivalence failed; no formal pair launch.'
        launch_env=runtime_environment(dict(project=str(args.pin),python=sys.executable))
        launches=[]
        for mode,eval_gpu in [('masked',0),('tracking',1)]:
            name='wuji_student_controller_%s_smallcp25_seed65_v2'%mode
            command=[sys.executable,'-m','scripts.run_reference_experiment','--manifest',str(args.pin/'wuji_student_controller_suite.json'),'--name',name]
            log=(args.output/(mode+'-pipeline.log')).open('w')
            child=subprocess.Popen(command,cwd=args.pin,env=launch_env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            queue=args.root/'runs/wuji-goal'/('audit-queue-student-controller-%s-smallcp25-seed65-v2.json'%mode)
            ecommand=[sys.executable,'-m','scripts.run_wuji_goal_audits','--queue',str(queue),'--gpu',str(eval_gpu),'--checkpoint-wait-seconds','14400']
            elog=(args.output/(mode+'-evaluations.log')).open('w')
            evaluator=subprocess.Popen(ecommand,cwd=args.pin,env=launch_env,stdout=elog,stderr=subprocess.STDOUT,start_new_session=True)
            launches.append(dict(mode=mode,owner='eight',training_pid=child.pid,evaluation_pid=evaluator.pid,evaluation_gpu=eval_gpu,
                command=command,evaluation_command=ecommand))
        record.update(status='pipelines_launched_after_runtime_gates',finished=now(),launches=launches,
                      note='Each pipeline must complete its own3real PPO epochs and gates before formal100epochtraining.')
        atomic_json(args.output/'status.json',record)
    except BaseException as error:
        record.update(status='failed',error=repr(error),finished=now())
        atomic_json(args.output/'status.json',record)
        raise


if __name__=='__main__':
    main()
