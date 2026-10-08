"""SDK process isolation and measured signs/zero conversion; commands in radians."""
import json,socket,subprocess,time,sys,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
class SDKBackend:
    def __init__(self,bundle,sdk_python,serial=None,motion=False,fixture=False,calibration=None,log=None,provisional_check=False):
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
                if s.get('format')!='wuji-device-calibration-v1':raise ValueError('Invalid calibration format')
                if motion and not provisional_check and not s.get('axes_zeros_limits_verified'):raise ValueError('Axes/zeros/device limits must be checked locally before motion')
                if motion and not provisional_check and not fixture and s.get('device_identity_sha256')!=self.header['device_identity_sha256']:raise ValueError('Device calibration belongs to another identified hand')
                spec=json.loads(Path(bundle).read_text())
                if s['runtime_joint_names']!=spec['runtime_joint_names']:raise ValueError('Calibration joint order mismatch')
                self.sign=np.asarray(s['model_from_device_sign'],dtype=float);self.zero=np.asarray(s['device_zero_rad'],dtype=float)
                if self.sign.shape!=(20,) or self.zero.shape!=(20,) or not np.all(np.isin(self.sign,[-1.,1.])) or not np.isfinite(self.zero).all():raise ValueError('Invalid signed zero mapping')
            elif motion and not fixture and not provisional_check:raise ValueError('Verified device calibration required for real motion')
            m=self.header['metadata'];a=self.to_model(m['lower_rad']['values']);b=self.to_model(m['upper_rad']['values']);self.lower=np.minimum(a,b);self.upper=np.maximum(a,b)
        except BaseException:
            self.close();raise
    def to_model(self,device):return self.sign*(np.asarray(device)-self.zero)
    def to_device(self,model):return np.asarray(model)*self.sign+self.zero
    def receive(self):
        r=self.f.readline()
        if not r:raise ConnectionError('SDK worker ended')
        v=json.loads(r)
        if not v.get('ok'):raise RuntimeError(v.get('error','SDK failure'))
        return v
    def request(self,op,**kwargs):self.f.write(json.dumps(dict(op=op,**kwargs))+'\n');self.f.flush();return self.receive()
    def read(self):
        r=self.request('read');v=r['data'];q=self.to_model(v['measured']['values'])
        if not np.isfinite(q).all():raise ValueError('Nonfinite device readings')
        if np.any(np.asarray(v['error_codes'])!=0):raise RuntimeError('Device reports joint errors')
        return q,v
    def write(self,model):
        if np.any(model<self.lower) or np.any(model>self.upper):raise ValueError('Device limits')
        r=self.request('write',target_rad=self.to_device(model).tolist())
        return self.to_model(r['data']['issued_target_rad']),r
    def stop(self):return self.request('stop')
    def close(self):
        if self.process.poll() is None:
            try:self.request('close')
            except Exception:pass
        self.f.close();self.sock.close()
        try:self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=1)
        if self.output!=subprocess.DEVNULL:self.output.close()
