"""Unified fixed-grasp entry: sim, read, empty-hand check, hold, response, push, stop.
Hardware uses the same RearController as sim through separate Python3.10 SDK IPC.
"""
import argparse,json,time,sys,select
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['sim','discover','read','check','hold','response','probe','push','stop']);p.add_argument('--bundle',type=Path,default=Path('research/rear-sim2real-20261009/bundle-deploy-v7.json'));p.add_argument('--output',type=Path);p.add_argument('--sdk-python',type=Path,default=Path('/data/research/artgym-experiments-20260921/contact-transfer-sdk310-venv/bin/python'));p.add_argument('--serial');p.add_argument('--fixture',action='store_true');p.add_argument('--motion-authorized',action='store_true');p.add_argument('--calibration',type=Path);p.add_argument('--pressure-response',type=Path);p.add_argument('--seconds',type=float,default=6);p.add_argument('--joint',type=int,default=17);p.add_argument('--step-rad',type=float,default=.01);p.add_argument('--stop-file',type=Path);p.add_argument('--external-jsonl',type=Path);a,extra=p.parse_known_args()
    if a.mode=='sim':
        from scripts.run_wuji_rear_sim import parser,main as sim
        argv=['--bundle',str(a.bundle),'--output',str(a.output)]+extra
        sim(parser().parse_args(argv));return
    if extra:p.error('Unsupported arguments '+str(extra))
    if a.mode=='discover':
        import subprocess
        subprocess.run([str(a.sdk_python),'-c','import json;from scripts.wuji_rear_sdk_worker import usb_inventory;print(json.dumps(usb_inventory()))'],cwd=ROOT,check=True);return
    if not a.output:p.error('--output is required')
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True)
    from scripts.wuji_rear_sdk_backend import SDKBackend
    motion=a.mode in ['check','hold','response','probe','push','stop']
    if motion and not a.motion_authorized:p.error('Real motor commands require explicit --motion-authorized (fixture is separately marked)')
    spec=json.loads(a.bundle.read_text());pressure=False
    if a.mode in ['hold','response','probe','push']:
        if spec.get('format')!='wuji-rear-bundle-v1':raise ValueError('Unknown bundle contract')
        for name,expected in spec['required_sha256'].items():
            if __import__('hashlib').sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Pinned dependency changed: '+name)
    if a.mode in ['probe','push']:
        if not a.pressure_response:raise ValueError('Push requires validated local position-response profile; no silent pressure-disable reproduction')
        response=json.loads(a.pressure_response.read_text())
        if response.get('format')!='wuji-local-response-v2' or not response.get('position_response_recorded') or not response.get('bounded_probe_permitted') or response.get('bundle_sha256')!=__import__('hashlib').sha256(a.bundle.read_bytes()).hexdigest():raise ValueError('Response profile does not validate this bundle')
        if response.get('source')!='hardware_local_response' and not a.fixture:raise ValueError('Fixture/simulation response cannot authorize hardware compensation')
        if not response.get('pressure_compensation_enabled'):raise ValueError('Complete controller requires explicit provisional pressure compensation enable after local position response')
        if not a.fixture and response.get('device_calibration_sha256')!=__import__('hashlib').sha256(a.calibration.read_bytes()).hexdigest():raise ValueError('Response/calibration mismatch')
        pressure=True
    b=SDKBackend(a.bundle,a.sdk_python,a.serial,motion,a.fixture,a.calibration,a.output/'sdk-console.log',provisional_check=a.mode in ['check','stop']);controller=None;rows=[];stop_reason=None
    (a.output/'metadata.json').write_text(json.dumps(b.header,indent=2))
    f=(a.output/'control.jsonl').open('w');tf=(a.output/'timing.jsonl').open('w');start=time.monotonic();previous_full_ms=None;consecutive_late=0;overruns=0
    def cycle(raw=None,phase='read'):
        nonlocal consecutive_late,overruns,previous_full_ms
        begin_ns=time.monotonic_ns();begin=time.monotonic();q,telemetry=b.read();read_end_ns=time.monotonic_ns();sent=None;action=None;write_timing=None;compute_end_ns=read_end_ns
        if controller:controller.observe(q)
        if raw is not None:
            wanted=np.asarray(raw(q) if callable(raw) else raw)
            if controller:sent=controller.constrain(wanted,b.lower,b.upper)
            else:sent=np.clip(wanted,b.lower,b.upper)
            compute_end_ns=time.monotonic_ns();sent,ack=b.write(sent);write_timing=b.last_write_timing.copy()
            if controller:controller.commit(sent);action=controller.last_action.copy()
        force_sample=None
        if a.external_jsonl:
            samples=[json.loads(line) for line in a.external_jsonl.read_text().splitlines() if line.strip()]
            for sample in samples:
                if sample.get('axis') not in ['normal','axial'] or not np.isfinite(sample['force_N']) or 'host_monotonic_ns' not in sample or not sample.get('source'):raise ValueError('Force log requires axis, N, host time and source')
            if samples:
                now=time.monotonic_ns();value=min(samples,key=lambda v:abs(v['host_monotonic_ns']-now));force_sample=dict(value,age_ns=now-value['host_monotonic_ns'],alignment_only=True)
        duration=time.monotonic()-begin
        row=dict(cycle_id=len(rows),host_cycle_start_ns=begin_ns,host_read_sample_ns=(telemetry['host_before_ns']+telemetry['host_after_ns'])//2,host_read_window_ns=[telemetry['host_before_ns'],telemetry['host_after_ns']],read_timing=b.last_read_timing.copy(),write_timing=write_timing,host_compute_ms=(compute_end_ns-read_end_ns)/1e6,previous_cycle_end_to_end_ms=previous_full_ms,elapsed_s=time.monotonic()-start,phase=phase,source='sdk_fixture_no_device' if a.fixture else 'hardware_sdk',encoder_model_rad=q.tolist(),device_telemetry=telemetry,external_force=force_sample,raw_target_rad=None if raw is None else wanted.tolist(),issued_target_rad=None if sent is None else sent.tolist(),executed_action=None if action is None else action.tolist(),loop_ms=duration*1000);rows.append(row);f.write(json.dumps(row)+'\n');f.flush();control_flush_ns=time.monotonic_ns();timing=dict(cycle_id=row['cycle_id'],host_cycle_start_ns=begin_ns,host_control_flush_ns=control_flush_ns,end_to_end_ms=(control_flush_ns-begin_ns)/1e6,record_ms=(control_flush_ns-begin_ns)/1e6-duration*1000,scope='Includes read/compute/write/ack/control JSON serialization+flush; excludes this small timing record. Next control row previous_cycle_end_to_end_ms includes timing record too.')
        tf.write(json.dumps(timing)+'\n');tf.flush();row['end_to_end_ms']=(time.monotonic_ns()-begin_ns)/1e6;previous_full_ms=row['end_to_end_ms']
        consecutive_late=consecutive_late+1 if row['end_to_end_ms']>1000/30 else 0;overruns+=row['end_to_end_ms']>1000/30
        if consecutive_late>=3:raise TimeoutError('Three full control cycles exceed 33.33ms; inspect timing, do not lower policy frequency')
        if a.stop_file and a.stop_file.exists():raise KeyboardInterrupt('Stop file')
        return q
    def run_for(seconds,func=None,phase='read'):
        began=time.monotonic();i=0
        while time.monotonic()-began<seconds:
            cycle(func(i/30) if func else None,phase);i+=1;time.sleep(max(0,began+i/30-time.monotonic()))
    def operator_wait(prompt):
        if a.fixture:return
        print(prompt+' 输入 go 后继续；Ctrl+C 停止并失能。',flush=True)
        while True:
            run_for(1/30,lambda t:controller.propose_hold(controller.issued),'operator_hold')
            if select.select([sys.stdin],[],[],0)[0]:
                answer=sys.stdin.readline().strip().lower()
                if answer=='go':return
                if answer in ['stop','quit','']:raise KeyboardInterrupt('Operator stopped')
    try:
        if a.mode=='stop':b.stop();stop_reason='explicit firmware disable';return
        if a.mode=='read':run_for(a.seconds);return
        q,_=b.read()
        if a.mode=='check':
            if abs(a.step_rad)>.015 or not 0<=a.joint<20:raise ValueError('Empty-hand test <=.015rad on one named runtime joint')
            def target(t):
                v=q.copy();v[a.joint]+=a.step_rad*np.sin(np.pi*min(t/a.seconds,1));return v
            run_for(a.seconds,lambda t:target(t),'empty_hand_one_joint');return
        # Load models while preserving existing firmware target. Never warm with sent commands.
        from scripts.wuji_rear_controller import RearController
        controller=RearController(spec,pressure_enabled=pressure,operation=a.mode);q,_=b.read();controller.seed_issued(q)
        from scripts.run_wuji_rear_sim import smooth
        opened=np.asarray(spec['open_q_rad']);initial=q.copy()
        run_for(3,lambda t:controller.propose_hold(initial+smooth(t/3)*(opened-initial)),'empty_approach')
        operator_wait('按图摆刀，暂时托住刀尾，确认拇指/滑块落点')
        initial=controller.issued.copy();hold=np.asarray(spec['hold_target_rad'])
        run_for(3,lambda t:controller.propose_hold(initial+smooth(t/3)*(hold-initial)),'close_with_external_support')
        operator_wait('缓慢撤去外部承托；确认刀无滚动、掉落或持续滑移')
        controller.policy.history=[] # Begin real unsupported history, do not fabricate frames.
        run_for(max(2,a.seconds if a.mode=='hold' else 2),lambda t:controller.propose_hold(hold),'independent_hold_history')
        if a.mode=='hold':return
        if a.mode=='response':
            if abs(a.step_rad)>.01 or a.joint not in range(16,20):raise ValueError('Local loaded thumb response <=.01rad')
            operator_wait('保持刀身承托，确认局部拇指响应方向；如用力计，单轴记录法向')
            anchor=controller.issued.copy()
            def local(t):
                from scripts.wuji_rear_diagnostics import local_response_target
                return controller.propose_hold(local_response_target(anchor,a.joint,a.step_rad,t,a.seconds))
            run_for(a.seconds+2,lambda t:local(t),'loaded_local_response');return
        operator_wait('确认仅靠手持刀且已完成局部响应检查；准备闭环推动')
        q,_=b.read();controller.takeover(q)
        # Recollect current real samples after isolated warmup; warmup sends no motion.
        run_for(50/30,lambda t:controller.propose_hold(controller.issued),'post_warm_real_history')
        run_for(spec['push_seconds'],lambda t:lambda q:controller.propose_push(q,t),'closed_loop_probe_and_hold' if a.mode=='probe' else 'closed_loop_push_and_hold')
        operator_wait(('用刻度和视频检查5mm试推、承托与落点' if a.mode=='probe' else '用刻度和视频确认实际推进 >20mm 且保持约1秒')+'；托住刀后输入 go 结束')
    except (KeyboardInterrupt,Exception) as e:
        stop_reason=type(e).__name__+': '+str(e)
        if motion:
            try:b.stop()
            except Exception as se:stop_reason+='; disable failed: '+str(se)
        if not isinstance(e,KeyboardInterrupt):raise
    finally:
        f.close();tf.close();ms=np.array([r.get('end_to_end_ms',r['loop_ms']) for r in rows]);summary=dict(source='sdk_fixture_no_device' if a.fixture else 'hardware_sdk',real_robot_ran=not a.fixture and motion,mode=a.mode,samples=len(rows),stop_reason=stop_reason,loop_ms=dict(p50=float(np.median(ms)) if len(ms) else None,p95=float(np.quantile(ms,.95)) if len(ms) else None,max=float(ms.max()) if len(ms) else None,over33ms=int(overruns)),controller=None if controller is None else controller.summary(),completion_scope='Hardware functional completion requires ruler/video; no slider truth input or automatic success claim')
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2));b.close()
        print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
