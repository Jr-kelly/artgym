"""Gate fixed sensor errors and feedback delays before full frozen-teacher diagnostics."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);args=p.parse_args()
    spec=json.loads(args.spec.read_text());pin=Path(__file__).resolve().parents[1]
    out=Path(spec['output']);out.mkdir(exist_ok=False)
    state=dict(status='starting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    try:
        modes=['full','position_bias_0p5mm','position_bias_2mm','rotation_bias_0p5deg','rotation_bias_2deg','slider_bias_0p25mm','slider_bias_1mm','delay1','delay3','delay6']
        for runtime in [True,False]:
            for mode in modes:
                name=('runtime-' if runtime else '')+mode
                lease=None
                while lease is None:
                    lease=acquire_evaluation_gpu(spec['gpu'])
                    if lease is None:time.sleep(10)
                destination=out/name
                cmd=[sys.executable,'-m','scripts.probe_wuji_teacher_sensor_accuracy','--output',str(destination),
                     '--mode',mode,'--seconds',str(spec['seconds'])]
                if runtime:cmd.append('--runtime-check')
                try:
                    with (out/(name+'.log')).open('w') as log:
                        child=subprocess.Popen(cmd,cwd=pin,
                            env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                        row=dict(name=name,pid=child.pid,status='running',started=now(),command=cmd)
                        state['status']=name;state['stages'].append(row);atomic_json(out/'status.json',state)
                        code=child.wait()
                finally:lease.close()
                row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                atomic_json(out/'status.json',state);assert code==0,row
                report=json.loads((destination/'input-probe-report.json').read_text())
                assert report['status']=='passed' and report['weights_unchanged']
                row['report']=report;atomic_json(out/'status.json',state)
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now());atomic_json(out/'status.json',state)
        raise


if __name__=='__main__':main()
