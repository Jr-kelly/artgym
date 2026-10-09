"""Private, pinned network executor IPC; no manufacturer source or USB dependency."""
import contextlib
import hashlib
import json
import socket
import subprocess
import time
from pathlib import Path
import numpy as np


def network_config(field):
    config = (field or {}).get('execution', {})
    if config.get('backend') != 'corobot-unified-v1':
        raise ValueError('Configure the unified arm/hand network executor')
    for key in ['backend_python', 'backend_script', 'profile']:
        if not Path(config[key]).is_file():
            raise ValueError('Missing network executor file: ' + key)
    pins = config.get('source_sha256', {})
    if str(Path(config['backend_script']).resolve()) not in pins:
        raise ValueError('Pin the actual network executor and its imported private helpers')
    for path, expected in pins.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Network executor source changed: ' + path)
    if hashlib.sha256(Path(config['profile']).read_bytes()).hexdigest() != config['profile_sha256']:
        raise ValueError('Field profile changed; review and bind its actual mapping again')
    return config


class NetworkBackend:
    def __init__(self, field, bundle, output, motion=False, allow_replay=False):
        config = network_config(field)
        expected_scope = 'offline_contract_no_device' if allow_replay else 'hardware_field'
        profile = json.loads(Path(config['profile']).read_text())
        if profile.get('evidence_scope') != expected_scope:
            raise ValueError('Fixture/hardware provenance mismatch; no execution connection created')
        left, right = socket.socketpair();left.settimeout(5)
        self.sock = left;self.stream = left.makefile('rw', encoding='utf-8', buffering=1)
        self.log = (Path(output)/'network-console.log').open('w')
        self.successful_writes = 0;self.g2_actual_state = None
        from scripts.host_tool_environment import host_tool_environment
        command = [config['backend_python'], config['backend_script'], '--fd', str(right.fileno()),
                   '--profile', config['profile'], '--bundle', str(bundle), '--output', str(output)]
        if motion:command += ['--motion-authorized']
        self.process = subprocess.Popen(command, env=host_tool_environment(), pass_fds=(right.fileno(),),
                                        stdout=self.log, stderr=self.log)
        right.close()
        try:
            self.header = self.receive()
            self.header['network_profile_sha256'] = config['profile_sha256']
            if self.header['evidence_scope'] != expected_scope:
                raise ValueError('Executor header/profile provenance mismatch')
            self.lower = np.array(self.header['lower']);self.upper = np.array(self.header['upper'])
            self.speed = np.array(self.header['speed'])
        except BaseException:
            self.close();raise

    def receive(self):
        line = self.stream.readline()
        if not line:raise ConnectionError('Network executor disconnected; physical state unconfirmed')
        value = json.loads(line)
        if not value['ok']:raise RuntimeError(value.get('error', 'Network executor failed'))
        self.successful_writes = value.get('successful_position_writes', self.successful_writes)
        return value

    def request(self, op, **kw):
        self.stream.write(json.dumps(dict(op=op, **kw))+'\n');self.stream.flush()
        return self.receive()

    def prepare(self):
        self.sock.settimeout(70)
        try:self.g2_actual_state = self.request('prepare')['sample']
        finally:self.sock.settimeout(.06)
        return self.g2_actual_state

    def read(self):
        start = time.monotonic_ns();r = self.request('read');end = time.monotonic_ns()
        self.last_read_timing = dict(host_request_start_ns=start, host_ack_ns=end,
                                    host_ipc_roundtrip_ms=(end-start)/1e6, sdk_operation_ms=None)
        self.g2_actual_state = r['data']['g2_actual_state']
        return np.array(r['q']), r['data']

    def write(self, model):
        start = time.monotonic_ns();r = self.request('write', target_rad=np.asarray(model).tolist());end = time.monotonic_ns()
        receipt = r['receipt'];self.last_receipt = receipt
        self.last_write_timing = dict(host_request_start_ns=start, host_ack_ns=end,
            host_ipc_roundtrip_ms=(end-start)/1e6, sdk_operation_ms=None,
            host_network_send_ns=receipt['host_send_start_ns'], host_network_ack_ns=receipt['host_ack_ns'],
            receipt_sequence=receipt['sequence'], request_sha256=receipt['request_sha256'],
            history_semantics=r['history_semantics'], actuator_target_confirmed=False)
        return np.array(r['sent']), r

    @contextlib.contextmanager
    def pause_hold(self):
        self.request('pause_hold', enabled=True)
        try:yield
        finally:self.request('pause_hold', enabled=False)

    def stop(self):return self.request('stop')
    def enable(self):raise RuntimeError('Use verified GDT/device initialization while empty; no audited enable RPC')
    def close(self):
        if self.process.poll() is None:
            try:self.sock.settimeout(.1);self.request('close')
            except (OSError, ValueError, RuntimeError, ConnectionError):pass
        self.stream.close();self.sock.close()
        try:self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=2)
        self.log.close()
