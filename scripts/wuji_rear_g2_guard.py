"""Same-host IPC to the separately pinned, private manufacturer bridge."""
import hashlib
import json
import os
import socket
import subprocess
import time
from pathlib import Path


def bridge_config(field):
    if not field or field.get('g2', {}).get('backend') != 'corobot-local-v1':
        raise RuntimeError('Configure the verified CoRobot bridge and field profile; legacy G2 asset alone cannot authorize hardware targets')
    config = field['g2']
    for name in ['backend_python', 'backend_script', 'profile']:
        if not Path(config[name]).is_file():
            raise RuntimeError('Missing G2 bridge file: ' + name)
    actual = hashlib.sha256(Path(config['backend_script']).read_bytes()).hexdigest()
    if actual != config['backend_sha256']:
        raise RuntimeError('Private G2 bridge changed; inspect and re-pin its source')
    return config


class G2Guard:
    def __init__(self, field, bundle, output, allow_replay=False):
        config = bridge_config(field)
        left, right = socket.socketpair()
        left.settimeout(20)
        self.sock = left
        self.stream = left.makefile('rw', encoding='utf-8', buffering=1)
        self.log = (Path(output) / 'g2-console.log').open('w')
        from scripts.host_tool_environment import host_tool_environment
        self.process = subprocess.Popen(
            [config['backend_python'], config['backend_script'], '--fd', str(right.fileno()),
             '--profile', config['profile'], '--bundle', str(bundle), '--output', str(output)],
            env=host_tool_environment(), pass_fds=(right.fileno(),), stdout=self.log, stderr=self.log)
        right.close()
        try:
            self.header = self.receive()
            if self.header['evidence_scope'] != 'hardware_field' and not allow_replay:
                raise RuntimeError('Offline CoRobot packets cannot authorize a hardware session')
        except BaseException:
            self.close()
            raise

    def receive(self):
        line = self.stream.readline()
        if not line:
            raise ConnectionError('CoRobot bridge ended; physical G2 stop is unconfirmed')
        value = json.loads(line)
        if not value['ok']:
            raise RuntimeError(value['error'])
        return value

    def request(self, operation):
        self.stream.write(json.dumps({'op': operation}) + '\n')
        self.stream.flush()
        return self.receive()

    def prepare(self):
        self.sock.settimeout(70)
        return self.request('prepare')

    def sample(self):
        if self.process.poll() is not None:
            raise ConnectionError('CoRobot hold process ended')
        self.sock.settimeout(.05)
        sample = self.request('sample')['sample']
        age_ns = time.monotonic_ns() - sample['host_received_ns']
        if not 0 <= age_ns <= 150_000_000 or not sample['at_target']:
            raise RuntimeError('G2 feedback stale or arm/body departed from verified fixed posture')
        return dict(sample, host_cache_age_ns=age_ns)

    def close(self):
        # Closing IPC is not an assertion of motor disable or a new arm target.
        if self.process.poll() is None:
            try:
                self.sock.settimeout(.2)
                self.request('close')
            except (OSError, RuntimeError, ConnectionError):
                pass
        self.stream.close()
        self.sock.close()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=2)
        self.log.close()
