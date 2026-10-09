"""Wuji continuous session with unified CoRobot network execution or legacy SDK.
Read-only paths need SDK Python/numpy only; policy/simulation imports stay lazy.
"""
import argparse,json,time,sys,select,os,subprocess,hashlib,gc,contextlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def assert_task_compatible(spec,lower,upper):
    reserve=spec.get('issued_limit_reserve_rad',0)
    nominal_lo=np.asarray(spec['model_lower_rad'])+reserve;nominal_hi=np.asarray(spec['model_upper_rad'])-reserve
    lo=np.maximum(nominal_lo,lower+reserve);hi=np.minimum(nominal_hi,upper-reserve)
    envelope=spec['deployment_required_target_envelope']
    conflicts=[]
    for i,n in enumerate(spec['runtime_joint_names']):
        for label,value in [('required_min',envelope['lower_rad'][i]),('required_max',envelope['upper_rad'][i])]:
            delta=float(np.clip(value,lo[i],hi[i])-value)
            if abs(delta)>1e-6:conflicts.append(dict(joint=n,target=label,required_rad=value,device_corridor=[float(lo[i]),float(hi[i])],would_change_rad=delta))
    if conflicts:raise ValueError('Device limits would change task trajectory: '+json.dumps(conflicts))
    return dict(scope='Pinned open/hold and saved full nominal actually-issued command envelope, not untested generalization',nominal_hold_clip_rad=(np.clip(spec['hold_target_rad'],nominal_lo,nominal_hi)-spec['hold_target_rad']).tolist())

def verified_field_speed(field,spec):
    w=field['wuji'];v=np.asarray(w.get('hardware_max_joint_speed_rad_s'),dtype=float)
    if v.shape!=(20,) or not np.isfinite(v).all() or np.any(v<=0) or not w.get('speed_source'):raise ValueError('Field config needs twenty verified hardware max_joint_speed_rad_s and their manufacturer/firmware source; .025rad/frame is a model cap, not a verified device speed')
    required=np.asarray(spec['deployment_required_target_envelope']['maximum_issued_speed_rad_s'])
    if np.any(v+1e-6<required):raise ValueError('Verified device speed cannot reproduce full task: '+json.dumps([dict(joint=spec['runtime_joint_names'][i],required_rad_s=float(required[i]),device_rad_s=float(v[i])) for i in np.flatnonzero(v+1e-6<required)]))
    return v

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['sim','discover','read','check','enable','hold','response','probe','push','session','stop']);p.add_argument('--bundle',type=Path,default=Path('research/rear-sim2real-20261009/bundle-deploy-v11.json'));p.add_argument('--output',type=Path);p.add_argument('--sdk-python',type=Path,default=Path(os.environ.get('WUJI_SDK_PYTHON',sys.executable)));p.add_argument('--serial');p.add_argument('--fixture',action='store_true');p.add_argument('--motion-authorized',action='store_true');p.add_argument('--calibration',type=Path);p.add_argument('--pressure-response',type=Path);p.add_argument('--seconds',type=float,default=6);p.add_argument('--response-seconds',type=float,default=2);p.add_argument('--joint',type=int,default=17);p.add_argument('--step-rad',type=float,default=.01);p.add_argument('--stop-file',type=Path);p.add_argument('--external-jsonl',type=Path);p.add_argument('--field-config',type=Path);p.add_argument('--empty-hand-confirmed',action='store_true');p.add_argument('--control-dir',type=Path);a,extra=p.parse_known_args()
    if a.mode=='sim':
        from scripts.run_wuji_rear_sim import parser,main as sim
        sim(parser().parse_args(['--bundle',str(a.bundle),'--output',str(a.output)]+extra));return
    if extra:p.error('Unsupported arguments '+str(extra))
    if not np.isfinite([a.seconds,a.response_seconds,a.step_rad]).all() or a.seconds<=0 or a.response_seconds<=0 or not 0<=a.joint<20:raise ValueError('Invalid duration/joint/step')
    from scripts.host_tool_environment import host_tool_environment
    if a.mode=='discover':
        subprocess.run([str(a.sdk_python),'-c','import json;from scripts.wuji_rear_sdk_worker import usb_inventory;print(json.dumps(usb_inventory()))'],cwd=ROOT,env=dict(host_tool_environment(),PYTHONPATH=str(ROOT)),check=True);return
    if not a.output:p.error('--output is required')
    motion=a.mode not in ['read'];loaded=a.mode in ['hold','response','probe','push','session']
    if motion and not a.motion_authorized:p.error('Real motor writes need --motion-authorized; fixture remains explicitly labelled')
    if motion and a.mode!='stop' and not a.empty_hand_confirmed:raise ValueError('Restart has no reliable loaded command memory: unload knife first, then --empty-hand-confirmed; no automatic loaded reinitialization')
    field=None
    if a.field_config:
        from scripts.wuji_rear_field import read_config,estimates
        field=read_config(a.field_config)
    network=bool(field and field.get('execution',{}).get('backend')=='corobot-unified-v1')
    if network and a.mode=='enable':raise ValueError('Use existing GDT/device initialization, not USB enable')
    if loaded and (not a.fixture or network or (field and field.get('g2',{}).get('backend')=='corobot-local-v1')):
        from scripts.wuji_rear_field import require_g2
        require_g2(field)
    if (a.mode=='enable' or loaded) and not a.fixture and not (field and field['wuji']['position_mode_verified'] and field['wuji']['position_mode_source']):raise ValueError('Use official firmware tool to confirm position mode first; no mode/enable readback in SDK 1.8.0. Record source in field config.')
    bundle_bytes=a.bundle.read_bytes();bundle_sha=hashlib.sha256(bundle_bytes).hexdigest();spec=json.loads(bundle_bytes);pressure=a.mode in ['probe','push','session'];device_speed=None
    if loaded:
        if spec.get('format')!='wuji-rear-bundle-v1':raise ValueError('Unknown bundle')
        for name,expected in spec['required_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Pinned dependency changed: '+name)
        if field:spec=estimates(spec,field)
        if not a.fixture:device_speed=verified_field_speed(field,spec)
    if a.mode in ['probe','push']:
        if not a.pressure_response:raise ValueError('Probe/push requires measured local response profile, or use continuous session')
        response=json.loads(a.pressure_response.read_text())
        if response.get('format')!='wuji-local-response-v2' or not response.get('position_response_recorded') or not response.get('bounded_probe_permitted') or not response.get('pressure_compensation_enabled') or response.get('bundle_sha256')!=hashlib.sha256(a.bundle.read_bytes()).hexdigest():raise ValueError('Invalid response/bundle binding')
        if not a.fixture and (response.get('source')!='hardware_local_response' or (not network and (not a.calibration or response.get('device_calibration_sha256')!=hashlib.sha256(a.calibration.read_bytes()).hexdigest()))):raise ValueError('Response/calibration/device source mismatch')
    operator=None
    if a.control_dir:
        if not network or a.mode!='session':raise ValueError('Operator channel is for the unified continuous session only')
        from scripts.wuji_rear_operator import OperatorControl
        operator=OperatorControl(a.control_dir)
        try:operator.wait_start()
        except BaseException:operator.close();raise
    if a.output.exists():
        if operator:operator.close()
        raise FileExistsError(a.output)
    a.output.mkdir(parents=True)
    (a.output/'bundle-at-run.json').write_bytes(bundle_bytes)
    from scripts.wuji_rear_sdk_backend import SDKBackend
    from scripts.wuji_rear_session import RearSession,DeadlineLoop,ExternalForceTail,smooth
    g2=None;g2_last=None
    if loaded and not network and (not a.fixture or (field and field.get('g2',{}).get('backend')=='corobot-local-v1')):
        from scripts.wuji_rear_g2_guard import G2Guard
        g2=G2Guard(field,a.bundle.resolve(),a.output.resolve(),allow_replay=a.fixture)
        try:
            g2.prepare();g2_last=g2.sample()
        except BaseException:
            g2.close();raise
    b=None
    try:
        if network:
            from scripts.wuji_rear_network_backend import NetworkBackend
            b=NetworkBackend(field,a.bundle,a.output,motion=motion,allow_replay=a.fixture)
            if a.mode in ['probe','push'] and (response.get('device_calibration_sha256')!=b.header['calibration_sha256'] or response.get('execution_profile_sha256')!=b.header['network_profile_sha256']):
                raise ValueError('Response belongs to a different network calibration/profile; no arm approach sent')
            if loaded:g2_last=b.prepare(on_wait=operator.poll if operator else None)
        else:b=SDKBackend(a.bundle,a.sdk_python,a.serial,motion,a.fixture,a.calibration,a.output/'sdk-console.log',provisional_check=a.mode in ['check','stop','enable'])
    except BaseException:
        if b is not None:b.close()
        if g2:g2.close()
        if operator:operator.close()
        raise
    controller=None;session=None;rows=[];stop_reason=None;stop_ack=None;analysis_process=None;events=[];gc_was_enabled=gc.isenabled()
    data_source=('offline_corobot_protocol_no_device' if a.fixture else 'hardware_corobot') if network else ('sdk_fixture_no_device' if a.fixture else 'hardware_sdk')
    b.header.update(bundle_sha256=bundle_sha,g2_actual_state=g2_last,g2_status='corobot_unified_arm_hand' if network else 'corobot_measured_guard' if g2 else 'absent_fixture_or_hand_only',initial_estimate=spec.get('field_initial_estimate',dict(source='saved_simulation_prior_unmeasured_on_hardware')),enabled_readback=None,control_mode_readback=None,device_verified_speed_rad_s=None if device_speed is None else device_speed.tolist())
    (a.output/'metadata.json').write_text(json.dumps(b.header,indent=2))
    f=(a.output/'control.jsonl').open('w');tf=(a.output/'timing.jsonl').open('w');start=time.monotonic();previous_full_ms=None;consecutive_late=0;overruns=0
    scheduler=DeadlineLoop();force_tail=ExternalForceTail(a.external_jsonl) if a.external_jsonl else None
    def event(name,**kw):
        v=dict(host_monotonic_ns=time.monotonic_ns(),phase=name,state=None if session is None else session.state,**kw);events.append(v)
        if operator:operator.update(phase=name,session_state=v['state'],placement_generation=None if session is None else session.generation)
        with (a.output/'session-events.jsonl').open('a') as ef:ef.write(json.dumps(v)+'\n')
    def cycle(raw=None,phase='read'):
        if operator:
            operator.poll()
            while operator.state['paused']:
                one_cycle(lambda q:controller.propose_hold(controller.issued),'operator_paused_hold')
                operator.poll()
        return one_cycle(raw,phase)
    def one_cycle(raw=None,phase='read'):
        nonlocal consecutive_late,overruns,previous_full_ms,g2_last
        if a.stop_file and a.stop_file.exists():raise KeyboardInterrupt('Stop file before next command')
        scheduler.tick();begin_ns=time.monotonic_ns();begin=time.monotonic();q,telemetry=b.read();read_end_ns=time.monotonic_ns();sent=None;action=None;write_timing=None;compute_end_ns=read_end_ns
        if g2:g2_last=g2.sample()
        if network:g2_last=b.g2_actual_state
        if controller:controller.observe(q)
        if raw is not None:
            wanted=np.asarray(raw(q) if callable(raw) else raw)
            if controller:
                # Reject new device-driven changes; original model reserve remains visible/logged.
                nominal=np.clip(wanted,controller.lower+spec.get('issued_limit_reserve_rad',0),controller.upper-spec.get('issued_limit_reserve_rad',0))
                dev=np.clip(nominal,b.lower+spec.get('issued_limit_reserve_rad',0),b.upper-spec.get('issued_limit_reserve_rad',0))
                if np.max(abs(dev-nominal))>1e-6:raise ValueError('Device corridor changes live target: '+json.dumps([dict(joint=spec['runtime_joint_names'][i],would_change_rad=float(dev[i]-nominal[i])) for i in np.flatnonzero(abs(dev-nominal)>1e-6)]))
                sent=controller.constrain(wanted,b.lower,b.upper)
                if device_speed is not None:
                    delta=sent-controller.issued;bound=device_speed/30
                    if np.any(abs(delta)>bound+1e-7):
                        if phase.startswith('closed_loop_'):raise ValueError('Live policy exceeds verified device speed; refused rather than slow full action')
                        sent=controller.issued+np.clip(delta,-bound,bound)
            else:
                if np.any(wanted<b.lower) or np.any(wanted>b.upper):raise ValueError('Named empty-hand target exceeds device limits; refused rather than clipped')
                sent=wanted
            compute_end_ns=time.monotonic_ns();sent,ack=b.write(sent);write_timing=b.last_write_timing.copy()
            if controller:controller.commit(sent);action=controller.last_action.copy()
        force_sample=force_tail.sample() if force_tail else None;duration=time.monotonic()-begin
        row=dict(cycle_id=len(rows),host_cycle_start_ns=begin_ns,host_read_sample_ns=(telemetry['host_before_ns']+telemetry['host_after_ns'])//2,host_read_window_ns=[telemetry['host_before_ns'],telemetry['host_after_ns']],read_timing=b.last_read_timing.copy(),write_timing=write_timing,host_compute_ms=(compute_end_ns-read_end_ns)/1e6,previous_cycle_end_to_end_ms=previous_full_ms,sample_gap_s=scheduler.last_gap,elapsed_s=time.monotonic()-start,phase=phase,session_state=None if session is None else session.state,placement_generation=None if session is None else session.generation,g2_actual_state=None,g2_state_source='absent_blocked',pressure_state='active_proxy_not_force' if controller and controller.taken and controller.policy.pressure_adapter is not None else 'armed_inactive' if pressure else 'disabled',initial_estimate_source=b.header['initial_estimate'],source=data_source,encoder_model_rad=q.tolist(),device_telemetry=telemetry,external_force=force_sample,raw_target_rad=None if raw is None else wanted.tolist(),issued_target_rad=None if sent is None else sent.tolist(),target_change_rad=None if sent is None else (sent-wanted).tolist(),executed_action=None if action is None else action.tolist(),loop_ms=duration*1000)
        row['g2_actual_state']=g2_last;row['g2_state_source']='corobot_remote_feedback' if g2 or network else 'absent_fixture_or_hand_only'
        rows.append(row);f.write(json.dumps(row)+'\n');f.flush();control_flush_ns=time.monotonic_ns();timing=dict(cycle_id=row['cycle_id'],host_cycle_start_ns=begin_ns,host_control_flush_ns=control_flush_ns,end_to_end_ms=(control_flush_ns-begin_ns)/1e6,record_ms=(control_flush_ns-begin_ns)/1e6-duration*1000,scope='Includes G2 guard, read/compute/write/ack/control flush; next row and summary include timing write')
        tf.write(json.dumps(timing)+'\n');tf.flush();row['end_to_end_ms']=(time.monotonic_ns()-begin_ns)/1e6;previous_full_ms=row['end_to_end_ms']
        consecutive_late=consecutive_late+1 if previous_full_ms>1000/30 else 0;overruns+=previous_full_ms>1000/30
        if consecutive_late>=3:raise TimeoutError('Three full cycles exceed 33.33ms; no frequency reduction')
        if a.stop_file and a.stop_file.exists():raise KeyboardInterrupt('Stop file')
        return q
    def run_for(seconds,func=None,phase='read'):
        # Exact 30Hz logical frame clock, actual sampling logged; never catch up.
        for i in range(round(seconds*30)):cycle(func(i/30) if func else None,phase)
    def operator_wait(prompt,gate):
        if a.fixture and not operator:event('fixture_operator_confirmation',prompt=prompt);return
        if operator:operator.gate(gate,prompt)
        instruction=(' 在另一终端运行 next --gate '+gate if operator else ' 输入 go')
        print(prompt+instruction+'；等待期间维持最后成功下发目标。Ctrl+C 终止软件流；先托刀并按现场设备停止流程处理。',flush=True)
        while True:
            cycle(lambda q:controller.propose_hold(controller.issued),'operator_hold')
            if operator:
                if operator.approved:
                    operator.update(gate=None,prompt=None);return
                continue
            if select.select([sys.stdin],[],[],0)[0]:
                answer=sys.stdin.readline().strip().lower()
                if answer=='go':return
                if answer in ['stop','quit','']:raise KeyboardInterrupt('Operator stopped')
    def unload():
        session.wait_unload();event('waiting_unload')
        operator_wait('托住并完全取下刀；如下一轮完整推动，把滑块近端复位至刀尾30mm。确认空手后继续','unload-'+str(session.generation))
        session.unloaded();event('unloaded_confirmed')
    def placement():
        session.begin_open();event('waiting_placement')
        initial=controller.issued.copy();opened=np.asarray(spec['open_q_rad'])
        run_for(3,lambda t:lambda q:controller.propose_hold(initial+smooth(t/3)*(opened-initial)),'empty_approach')
        operator_wait('按图放刀，滑块近端距刀尾30mm；暂托刀尾并确认拇指落点','place-'+str(session.generation))
        session.placed();event('closing')
        initial=controller.issued.copy()
        run_for(3,lambda t:lambda q:session.target('close',q,t,initial),'close_with_external_support')
        operator_wait('缓慢撤去外部承托，确认刀无滚动或持续滑移','withdraw-'+str(session.generation))
        session.unsupported();event('loaded_hold')
        run_for(2,lambda t:lambda q:controller.propose_hold(controller.issued),'independent_hold_history')
    def push(operation):
        session.prepare_push(operation);event('prepare_'+operation)
        operator_wait('确认真实位置响应已检查、无滚转滑移；准备'+('5mm有界诊断' if operation=='probe' else '完整35mm请求（实测需>20mm）'),'prepare-'+operation+'-'+str(session.generation))
        # Clear old response/analysis history and collect actual new unsupported samples.
        controller.policy.history=[]
        run_for(50/30,lambda t:lambda q:controller.propose_hold(controller.issued),'fresh_pre_takeover_history')
        q=np.asarray(rows[-1]['encoder_model_rad'])
        with b.pause_hold() if network else contextlib.nullcontext():controller.takeover(q)
        event('isolated_warmup',commands_issued=controller.warmup['commands_issued'])
        scheduler.rebase_after_pause()
        # Model loading/warmup can take wall time; firmware target retained, schedule restarted.
        run_for(50/30,lambda t:lambda q:controller.propose_hold(controller.issued),'post_warm_real_history')
        run_for(spec['push_seconds'],lambda t:lambda q:session.target('push',q,t),'closed_loop_probe_and_hold' if operation=='probe' else 'closed_loop_push_and_hold')
        session.push_done();event('post_push_hold')
        operator_wait('用尺和视频检查实际行程、侧面滚转和保持；若试推失败输入 stop；通过后 go。不会据fixture自动判定接触成功','result-'+operation+'-'+str(session.generation))
    try:
        if a.stop_file and a.stop_file.exists():raise KeyboardInterrupt('Stop file before initialization')
        if a.mode=='stop':stop_ack=b.stop();stop_reason='explicit disable request acknowledged';return
        if a.mode=='read':run_for(a.seconds);return
        if a.mode=='enable':stop_ack=b.enable();event('enable_requested',ack=stop_ack);return
        q,_=b.read()
        if a.mode=='check':
            if abs(a.step_rad)>.015:raise ValueError('Empty check <=.015rad')
            def target(t):
                v=q.copy();v[a.joint]+=a.step_rad*np.sin(np.pi*min(t/a.seconds,1));return v
            run_for(a.seconds,target,'empty_hand_one_joint');return
        from scripts.wuji_rear_controller import RearController
        with b.pause_hold() if network else contextlib.nullcontext():
            controller=RearController(spec,pressure_enabled=pressure,operation='push' if a.mode=='session' else a.mode)
        scheduler.rebase_after_pause()
        # Refcount cleanup still runs. Cyclic collection is deferred to unloaded pauses;
        # two fixture runs had ~64ms IPC/host spikes at the same post-warm frame.
        gc.collect();gc.disable();event('cyclic_gc_deferred',scope='Short loaded session only; not proof of cause of earlier host spikes')
        compat=assert_task_compatible(spec,b.lower,b.upper);(a.output/'target-compatibility.json').write_text(json.dumps(compat,indent=2))
        q,_=b.read();controller.seed_issued(q)
        session=RearSession(controller);session.confirm_empty();event('empty_confirmed');scheduler.rebase_after_pause();placement()
        if a.mode=='hold':run_for(a.seconds,lambda t:lambda q:controller.propose_hold(controller.issued),'independent_hold_history');unload()
        elif a.mode in ['response','session']:
            if abs(a.step_rad)>.01 or a.joint not in range(16,20):raise ValueError('Loaded thumb response <=.01rad')
            session.response();event('response');anchor=controller.issued.copy()
            from scripts.wuji_rear_diagnostics import local_response_target
            run_for(a.response_seconds+2,lambda t:lambda q:controller.propose_hold(local_response_target(anchor,a.joint,a.step_rad,t,a.response_seconds)),'loaded_local_response')
            # Restore original preload with the same successful-command memory, no new connection.
            run_for(1/30,lambda t:lambda q:controller.propose_hold(anchor),'response_return_to_hold')
            session.response_done();event('analysis_hold')
            snapshot=a.output/'response';snapshot.mkdir();f.flush();tf.flush()
            (snapshot/'control.jsonl').write_text((a.output/'control.jsonl').read_text());(snapshot/'timing.jsonl').write_text((a.output/'timing.jsonl').read_text());(snapshot/'metadata.json').write_text(json.dumps(b.header,indent=2))
            # Analysis runs in another process while this connection continues position hold.
            analysis_process=subprocess.Popen([sys.executable,'-m','scripts.analyze_wuji_rear_response','--input',str(snapshot),'--output',str(a.output/'analysis')],cwd=ROOT,stdout=open(a.output/'analysis-console.log','w'),stderr=subprocess.STDOUT)
            while analysis_process.poll() is None:cycle(lambda q:controller.propose_hold(controller.issued),'analysis_hold')
            if analysis_process.returncode:raise RuntimeError('Response analysis failed; inspect analysis-console.log')
            analysis=json.loads((a.output/'analysis/analysis.json').read_text());event('analysis_ready',path=str(a.output/'analysis'),lag=analysis['lag']['status'])
            print('响应图：'+str(a.output/'analysis/response.png')+'；分析：'+str(a.output/'analysis/analysis.json'),flush=True)
            if a.mode=='session':
                if analysis['issued_amplitude_rad']<.003 or analysis['encoder_amplitude_rad']<.0005:raise ValueError('No measurable loaded response; inspect mapping/mode/preload')
                response_rows=[r for r in rows if r['phase']=='loaded_local_response']
                if max(r['end_to_end_ms'] for r in response_rows)>1000/30:raise TimeoutError('Local response full loop timing failed')
                operator_wait('检查响应图／方向／恢复偏置和接触视频；同意仅开启临时模型补偿做probe后输入 go（不是测力标定）','response-review-'+str(session.generation))
                profile=dict(format='wuji-local-response-v2',bundle_sha256=hashlib.sha256(a.bundle.read_bytes()).hexdigest(),device_calibration_sha256=b.header.get('calibration_sha256'),source='offline_corobot_protocol_no_device' if a.fixture and network else 'sdk_fixture_no_device' if a.fixture else 'hardware_local_response',execution_profile_sha256=b.header.get('network_profile_sha256'),position_response_recorded=True,bounded_probe_permitted=True,pressure_compensation_enabled=True,normal_force_calibrated=False,full_action_reliability='not_established',response_analysis=[analysis])
                (a.output/'response-verified.json').write_text(json.dumps(profile,indent=2))
                push('probe');unload()
                # New object placement, new policy/history/RNN/estimate; preserve current unloaded target.
                issued=controller.issued.copy()
                with b.pause_hold() if network else contextlib.nullcontext():controller=RearController(spec,pressure_enabled=True,operation='push')
                controller.seed_issued(issued)
                gc.collect();event('unloaded_collection_pause')
                scheduler.rebase_after_pause()
                session.c=controller;event('new_placement_generation',slider_near_edge_mm=30,initial_estimate=spec.get('field_initial_estimate'))
                placement();push('push');unload()
            else:unload()
        else:push(a.mode);unload()
        stop_ack=b.stop();stop_reason='normal unloaded end: network stream ends; physical disable unconfirmed' if network else 'normal unloaded end: firmware disable request acknowledged; G2 unaffected';event('finished',disable_ack=stop_ack)
    except (KeyboardInterrupt,Exception) as e:
        stop_reason=type(e).__name__+': '+str(e);event('aborted',reason=stop_reason,last_read_timing=getattr(b,'last_read_timing',None),rejected_sample=getattr(b,'last_read_rejection',None))
        if motion:
            try:stop_ack=b.stop()
            except Exception as se:stop_reason+='; disable unconfirmed: '+str(se)
        if not isinstance(e,KeyboardInterrupt):raise
    finally:
        if analysis_process and analysis_process.poll() is None:analysis_process.terminate()
        if gc_was_enabled:gc.enable()
        f.close();tf.close();ms=np.array([r.get('end_to_end_ms',r['loop_ms']) for r in rows]);summary=dict(source=data_source,real_robot_ran=not a.fixture and b.successful_writes>0,mode=a.mode,samples=len(rows),successful_writes=b.successful_writes,stop_reason=stop_reason,stop_ack=stop_ack,physical_disabled_state_confirmed=False,g2_actual_state=None,g2_integration='blocked',loop_ms=dict(p50=float(np.median(ms)) if len(ms) else None,p95=float(np.quantile(ms,.95)) if len(ms) else None,max=float(ms.max()) if len(ms) else None,over33ms=int(overruns)),controller=None if controller is None else controller.summary(),completion_scope='Hardware success requires G2 integration, ruler/video >20mm and hold; fixture is software only')
        summary['g2_actual_state']=g2_last;summary['g2_integration']='corobot_unified_arm_hand' if network else 'corobot_guard' if g2 else 'absent_fixture_or_hand_only'
        summary['history_semantics']=b.header.get('history_semantics','sdk_issued_target');summary['downstream_processing']=b.header.get('downstream_processing');summary['local_usb_required']=not network;summary['g2_physical_stop_confirmed']=False
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2))
        try:b.close()
        finally:
            if g2:g2.close()
            if operator:operator.close()
        print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
