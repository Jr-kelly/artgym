"""Run frozen RGB/masked policy gates and all predeclared formal conditions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1];out=root/spec['output']
    assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state);lease=None;child=None
    try:
        if spec.get('wait_for'):
            while True:
                prior=root/spec['wait_for']/'status.json'
                previous=json.loads(prior.read_text()) if prior.exists() else {}
                assert previous.get('status')!='failed',previous.get('error')
                if previous.get('status')=='completed':break
                state.update(status='waiting_for_preflight',heartbeat=now());atomic_json(out/'status.json',state)
                time.sleep(10)
        if spec.get('lease_gpu',True):
            while lease is None:
                lease=acquire_evaluation_gpu(spec['gpu'])
                if lease is None:time.sleep(5)
            used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
            assert used<1000,(spec['gpu'],used)
        for stage in spec['stages']:
            arm=stage['arm'];artifact=root/spec['artifacts'][arm]['path']
            assert hashlib.sha256(artifact.read_bytes()).hexdigest()==spec['artifacts'][arm]['sha256']
            name=stage['name'];folder=out/name
            cmd=[sys.executable,'-m','scripts.eval_wuji_rgb_state_policy','--artifact',str(artifact),
                '--output',str(folder),'--seconds',str(stage['seconds']),
                '--graphics-device-id',str(spec['graphics_device_id'])]
            if spec.get('compute_device_id') is not None:
                cmd+=['--compute-device-id',str(spec['compute_device_id'])]
            if spec.get('ordered_cleanup'):cmd+=['--ordered-cleanup']
            if spec.get('verify_sensor_interface'):cmd+=['--verify-sensor-interface']
            if spec.get('sensor_interface_driver'):cmd+=['--sensor-interface-driver']
            if spec.get('sensor_matched_reference'):cmd+=['--sensor-matched-reference']
            if spec.get('sensor_active_parity'):cmd+=['--sensor-active-parity']
            if spec.get('record_video'):cmd+=['--record-video']
            if stage.get('runtime_check'):cmd+=['--runtime-check']
            if stage.get('initial_state_rows') is not None:
                cmd+=['--initial-state-rows']+list(map(str,stage['initial_state_rows']))
            if spec.get('initial_states'):
                initial_path=root/spec['initial_states']['path']
                assert hashlib.sha256(initial_path.read_bytes()).hexdigest()==spec['initial_states']['sha256']
                cmd+=['--initial-states',str(initial_path)]
            if 'evaluation_seed' in spec:cmd+=['--evaluation-seed',str(spec['evaluation_seed'])]
            env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu'])
            if spec.get('unmask_cuda_devices'):
                assert spec['compute_device_id']==spec['gpu']==spec['graphics_device_id']
                env.pop('CUDA_VISIBLE_DEVICES',None)
            env['VK_ICD_FILENAMES']=spec.get('vulkan_icd','/etc/vulkan/icd.d/nvidia_icd.json')
            if spec.get('runtime_library_paths'):
                env['LD_LIBRARY_PATH']=':'.join(spec['runtime_library_paths'])+':'+env.get('LD_LIBRARY_PATH','')
            with (out/(name+'.log')).open('w') as f:
                child=subprocess.Popen(cmd,cwd=pin,env=env,stdin=subprocess.DEVNULL,
                    stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),) if lease else ())
            row=dict(name=name,pid=child.pid,command=cmd,status='running',started=now())
            state['stages'].append(row);state['status']='evaluating';atomic_json(out/'status.json',state)
            code=child.wait();row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
            audit=json.loads((folder/'rgb-policy-audit.json').read_text())
            assert audit['status']=='passed' and audit['model_unchanged'] and audit['estimator_unchanged']
            assert not audit['current_truth_actor_input'] and audit['causal_velocity_recomputed']
            expected=3*600 if stage.get('runtime_check') else len(stage.get('initial_state_rows',range(332)))*600
            assert audit['checks']['physics_transitions']==expected
            if stage.get('runtime_check'):assert audit['checks']['privileged_invariance']==expected
            if stage.get('runtime_check') and arm=='masked':assert audit['checks']['masked_image_invariance']==3*599
            if spec.get('ordered_cleanup'):
                cleanup=json.loads((folder/'cleanup-status.json').read_text())
                assert cleanup['status']=='completed' and cleanup['sim_destroy_returned']
                assert cleanup['camera_count']==2*(expected//600)
            if spec.get('verify_sensor_interface'):
                assert audit['checks']['sensor_interface_rows']==expected
            if spec.get('sensor_interface_driver'):
                assert audit['sensor_interface_driver'] and audit['checks']['sensor_driver_rows']==expected
            if spec.get('sensor_active_parity'):
                assert audit['sensor_active_parity']
                assert audit['checks']['sensor_active_rows']+audit['checks']['sensor_retired_rows']==expected
            if spec.get('record_video'):assert audit['checks']['video_frames']==599
        state.update(status='completed',finished=now(),task_success_claim=False)
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        if child and child.poll() is None:child.terminate();child.wait(timeout=20)
        raise
    finally:
        atomic_json(out/'status.json',state)
        if lease:lease.close()


if __name__=='__main__':main()
