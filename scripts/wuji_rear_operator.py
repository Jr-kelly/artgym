"""Local operator commands for ONE existing rear controller; no motor backend."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import time


def address(directory):
    key = hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest()[:24]
    return '/tmp/wuji-rear-%s-%s.sock' % (os.getuid(), key)


class OperatorControl:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (self.directory/'operator.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.lock.close()
            raise RuntimeError('An existing rear session owns this operator directory')
        self.path = address(directory)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            if os.path.exists(self.path): os.unlink(self.path)
            self.socket.bind(self.path)
            os.chmod(self.path, 0o600)
            self.socket.setblocking(False)
        except BaseException:
            self.socket.close(); self.lock.close()
            raise
        self.state = dict(started=False, paused=False, phase='waiting_start',
                          session_state=None, gate=None, prompt=None,
                          physical_stop_confirmed=False)
        self.approved = False
        self.stopped = False
        self.log = (self.directory/'operator-events.jsonl').open('a')

    def update(self, **state):
        self.state.update(state)

    def gate(self, name, prompt):
        self.approved = False
        self.update(gate=name, prompt=prompt)

    def handle(self, request):
        command = request.get('command')
        if command == 'status': return dict(ok=True, **self.state)
        if command == 'start':
            if self.state['started']:
                return dict(ok=True, already_started=True, initialization_repeated=False)
            if not request.get('motion_authorized') or not request.get('empty_hand_confirmed'):
                return dict(ok=False, error='Start requires site motion authorization and confirmed empty hand')
            self.state['started'] = True
            return dict(ok=True, initialization_repeated=False)
        if command == 'next':
            if not self.state['gate'] or self.approved or request.get('gate') != self.state['gate']:
                return dict(ok=False, error='Confirm the current named gate exactly once; inspect status')
            if self.state['paused']:
                return dict(ok=False, error='Resume before confirming a gate')
            self.approved = True
            return dict(ok=True, gate=self.state['gate'])
        if command in ['pause', 'resume']:
            if not self.state['started']:
                return dict(ok=False, error='Session has not started')
            if self.state['phase']=='initializing':
                return dict(ok=False, error='Bounded empty initialization is running; stop is available, pause begins after arrival')
            self.state['paused'] = command == 'pause'
            return dict(ok=True, paused=self.state['paused'],
                        meaning='Same connection retains last RPC-accepted target; software acknowledgement, not motor state')
        if command == 'reset':
            return dict(ok=False, error='No external reset. At unload gate remove knife and reset slider to 30mm, then confirm that gate; restart only empty')
        if command == 'stop':
            self.stopped = True
            return dict(ok=True, software_stop_requested=True, physical_stop_confirmed=False)
        return dict(ok=False, error='Unknown operator command')

    def poll(self):
        # Bound work per 30Hz cycle; operator traffic cannot become an unbounded loop.
        for _ in range(4):
            try: data, peer = self.socket.recvfrom(4096)
            except BlockingIOError: break
            try:
                request = json.loads(data)
                result = self.handle(request)
            except (ValueError, TypeError, AttributeError) as error:
                request = {}; result = dict(ok=False, error=str(error))
            if request.get('command') != 'status':
                self.log.write(json.dumps(dict(host_monotonic_ns=time.monotonic_ns(),
                                               request=request, response=result))+'\n')
                self.log.flush()
            try: self.socket.sendto(json.dumps(result).encode(), peer)
            except OSError: pass  # A disconnected operator never resets or stops a session.
        if self.stopped: raise KeyboardInterrupt('Operator software stop; physical stop unconfirmed')

    def wait_start(self):
        print('ArtGym rear ready: waiting_start. Connect GDT robot, enable remote_env, then use rear-field start. No target sent yet.', flush=True)
        while not self.state['started']:
            self.poll(); time.sleep(.02)
        self.update(phase='initializing')

    def close(self):
        self.socket.close()
        if os.path.exists(self.path): os.unlink(self.path)
        self.log.close(); self.lock.close()


def request(directory, command, gate=None, motion_authorized=False, empty_hand_confirmed=False):
    with tempfile.TemporaryDirectory(prefix='rear-op-') as temporary:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            client.bind(str(Path(temporary)/'reply.sock')); client.settimeout(2)
            client.sendto(json.dumps(dict(command=command, gate=gate,
                motion_authorized=motion_authorized, empty_hand_confirmed=empty_hand_confirmed)).encode(), address(directory))
            return json.loads(client.recv(65536))
        finally: client.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument('command', choices=['status','start','next','pause','resume','reset','stop'])
    p.add_argument('--control-dir', type=Path, required=True); p.add_argument('--gate')
    p.add_argument('--motion-authorized', action='store_true'); p.add_argument('--empty-hand-confirmed', action='store_true')
    a=p.parse_args(); result=request(a.control_dir, a.command, a.gate, a.motion_authorized, a.empty_hand_confirmed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['ok']: raise SystemExit(2)


if __name__ == '__main__': main()
