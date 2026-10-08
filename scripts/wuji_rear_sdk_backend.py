"""SDK process isolation and measured signs/zero conversion; commands in radians."""
import json,socket,subprocess,time,sys,hashlib,os,fcntl,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
class SDKBackend:
    def __init__(self,bundle,sdk_python,serial=None,motion=False,fixture=False,calibration=None,log=None,provisional_check=False):
        self.lock=None;self.previous_sample=None;self.motion=motion;self.successful_writes=0;self.clock_fast=fixture;self.unchanged_clock_since=None
        if motion:
            key=hashlib.sha256(('fixture' if fixture else str(serial)).encode()).hexdigest()
            lockdir=Path(tempfile.gettempdir())/('wuji-rear-ownership-'+str(os.getuid()));lockdir.mkdir(mode=0o700,exist_ok=True)
            self.lock=(lockdir/(key+'.lock')).open('a+')
            try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock.close();raise RuntimeError('Another Wuji writer owns this serial; use its active-session stop, do not start another writer')
        left,right=socket.socketpair();left.settimeout(1.);self.sock=left;self.f=left.makefile('rw',encoding='utf-8',buffering=1)
        cmd=[str(sdk_python),'-m','scripts.wuji_rear_sdk_worker','--fd',str(right.fileno()),'--bundle',str(bundle)]
        if serial:cmd+=['--serial',serial]
        if motion:cmd+=['--motion-authorized']
        if fixture:cmd+=['--fixture']
        self.output=open(log,'a',encoding='utf-8') if log else subprocess.DEVNULL
        from scripts.host_tool_environment import host_tool_environment
        child_env=host_tool_environment();child_env['PYTHONPATH']=str(ROOT)
        self.process=subprocess.Popen(cmd,cwd=ROOT,env=child_env,pass_fds=(right.fileno(),),stdout=self.output,stderr=self.output);right.close()
        try:
            self.header=self.receive();self.header['device_identity_sha256']=hashlib.sha256(str(serial).encode()).hexdigest() if not fixture else None;self.sign=np.ones(20);self.zero=np.zeros(20)
            if calibration:
                s=json.loads(Path(calibration).read_text())
                self.header['calibration_sha256']=hashlib.sha256(Path(calibration).read_bytes()).hexdigest()
                self.clock_fast=fixture or s.get('system_clock_advances_at_30hz_observed',False)
                if s.get('format')!='wuji-device-calibration-v1':raise ValueError('Invalid calibration format')
                if motion and not provisional_check and not fixture and not (s.get('axes_verified') and s.get('absolute_zero_verified') and s.get('absolute_zero_evidence_sha256') and s.get('axes_zeros_limits_verified')):raise ValueError('Small motion does not verify absolute zero: import trusted zero evidence and verify axes first')
                if motion and not provisional_check and not fixture and not self.clock_fast:raise ValueError('Need real 30Hz read evidence that opaque SDK system clock advances per sample; its units are not established')
                if motion and not provisional_check and not fixture and s.get('device_identity_sha256')!=self.header['device_identity_sha256']:raise ValueError('Device calibration belongs to another identified hand')
                spec=json.loads(Path(bundle).read_text())
                if s['runtime_joint_names']!=spec['runtime_joint_names']:raise ValueError('Calibration joint order mismatch')
                self.sign=np.asarray(s['model_from_device_sign'],dtype=float);self.zero=np.asarray(s['device_zero_rad'],dtype=float)
                if self.sign.shape!=(20,) or self.zero.shape!=(20,) or not np.all(np.isin(self.sign,[-1.,1.])) or not np.isfinite(self.zero).all():raise ValueError('Invalid signed zero mapping')
            elif motion and not fixture and not provisional_check:raise ValueError('Verified device calibration required for real motion')
            m=self.header['metadata'];a=self.to_model(m['lower_rad']['values']);b=self.to_model(m['upper_rad']['values']);self.lower=np.minimum(a,b);self.upper=np.maximum(a,b)
            if calibration and motion and not provisional_check and not fixture:
                if not np.allclose(s.get('device_lower_rad',[]),m['lower_rad']['values'],rtol=0,atol=1e-6) or not np.allclose(s.get('device_upper_rad',[]),m['upper_rad']['values'],rtol=0,atol=1e-6):raise ValueError('Device limits changed since calibration; inspect named limits')
        except BaseException:
            self.close();raise
    def to_model(self,device):return self.sign*(np.asarray(device)-self.zero)
    def to_device(self,model):return np.asarray(model)*self.sign+self.zero
    def receive(self):
        r=self.f.readline()
        if not r:raise ConnectionError('SDK worker ended')
        v=json.loads(r)
        self.successful_writes=v.get('successful_position_writes',self.successful_writes)
        if not v.get('ok'):raise RuntimeError(v.get('error','SDK failure'))
        return v
    def request(self,op,**kwargs):self.f.write(json.dumps(dict(op=op,**kwargs))+'\n');self.f.flush();return self.receive()
    def read(self):
        begin=time.monotonic_ns();r=self.request('read');end=time.monotonic_ns();self.last_read_timing=dict(host_request_start_ns=begin,host_ack_ns=end,host_ipc_roundtrip_ms=(end-begin)/1e6,sdk_operation_ms=r.get('sdk_operation_ns',0)/1e6);v=r['data'];q=self.to_model(v['measured']['values'])
        if not np.isfinite(q).all():raise ValueError('Nonfinite device readings')
        if np.any(np.asarray(v['error_codes'])!=0):raise RuntimeError('Device reports joint errors')
        sample=(v['device_system_time_raw'],v['host_after_ns'])
        if self.previous_sample is not None:
            old,oldhost=self.previous_sample
            if sample[1]<=oldhost:raise ValueError('Out-of-order host encoder sample')
            if sample[0]==old:
                if self.unchanged_clock_since is None:self.unchanged_clock_since=oldhost
                threshold=20000000 if self.clock_fast else 2000000000
                if sample[1]-self.unchanged_clock_since>=threshold:raise TimeoutError('Device system time did not advance; stale data cannot enter history (clock scale not assumed)')
            else:self.unchanged_clock_since=None
            if (int(sample[0])-int(old))%(2**32)>=2**31:raise ValueError('Device clock reversed/reset; restart unloaded')
        if end-v['host_after_ns']>66666667 or v['host_after_ns']-v['host_before_ns']>66666667:
            self.last_read_rejection=dict(host_read_window_ns=[v['host_before_ns'],v['host_after_ns']],host_ack_ns=end,device_system_time_raw=v['device_system_time_raw'],read_timing=self.last_read_timing)
            raise TimeoutError('Encoder read/ack exceeds two 30Hz periods; sample rejected')
        self.previous_sample=sample
        return q,v
    def write(self,model):
        if np.any(model<self.lower) or np.any(model>self.upper):raise ValueError('Device limits')
        begin=time.monotonic_ns();r=self.request('write',target_rad=self.to_device(model).tolist());end=time.monotonic_ns();self.last_write_timing=dict(host_request_start_ns=begin,host_ack_ns=end,host_ipc_roundtrip_ms=(end-begin)/1e6,sdk_operation_ms=r.get('sdk_operation_ns',0)/1e6)
        return self.to_model(r['data']['issued_target_rad']),r
    def stop(self):return self.request('stop')
    def enable(self):return self.request('enable')
    def close(self):
        if self.process.poll() is None:
            try:self.request('close')
            except Exception:pass
        self.f.close();self.sock.close()
        try:self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=1)
        if self.output!=subprocess.DEVNULL:self.output.close()
        if self.lock is not None:self.lock.close();self.lock=None
