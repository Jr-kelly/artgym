"""Python3.10 / wujihandpy1.8 worker. No torch; direct mapped position API.
Only explicit motion mode permits writes; no implicit enable, reset or limit writes.
IPC uses a dedicated inherited socket, so SDK console output cannot become commands.
"""
import argparse,json,socket,time,gc
from pathlib import Path
import numpy as np
from isaacgymenvs.deploy.wuji.sdk_hand_api import WujiSDKHandAPI

def usb_inventory():
    rows=[]
    for p in Path('/sys/bus/usb/devices').iterdir():
        if not (p/'idVendor').is_file():continue
        vid=(p/'idVendor').read_text().strip();pid=(p/'idProduct').read_text().strip()
        if (vid,pid)==('0483','2000'):
            rows.append(dict(vid=vid,pid=pid,serial=(p/'serial').read_text().strip() if (p/'serial').exists() else None))
    return rows
class FixtureHand:
    """SDK-shaped fixture, no hardware and no physical inference claim."""
    def __init__(self,names):
        from isaacgymenvs.deploy.wuji.joint_mapping import WujiJointMapping
        self.m=WujiJointMapping(names);self.q=np.zeros((5,4));self.lower=np.full((5,4),-2.);self.upper=np.full((5,4),2.);self.writes=0
    def read_handedness(self):return 0
    def read_firmware_version(self):return 0
    def read_firmware_date(self):return 0
    def read_joint_lower_limit(self):return self.lower
    def read_joint_upper_limit(self):return self.upper
    def read_joint_effort_limit(self):return np.ones((5,4))
    def read_joint_actual_position(self):return self.q.copy()
    def read_joint_error_code(self):return np.zeros((5,4),np.uint32)
    def read_system_time(self):return int(time.monotonic()*1000)%(2**32)
    def write_joint_target_position(self,q):self.q=np.asarray(q).copy();self.writes+=1
    def write_joint_enabled(self,value):pass

def serve(a):
    bundle=json.loads(Path(a.bundle).read_text());sock=socket.socket(fileno=a.fd);stream=sock.makefile('rw',encoding='utf-8',buffering=1)
    api=WujiSDKHandAPI(bundle['runtime_joint_names'],serial=a.serial,hand=FixtureHand(bundle['runtime_joint_names']) if a.fixture else None,motion_authorized=a.motion_authorized)
    position_writes=0
    def reply(value):value['successful_position_writes']=position_writes;stream.write(json.dumps(value)+'\n');stream.flush()
    try:
        if not a.fixture:
            import wujihandpy
            if wujihandpy.__version__!='1.8.0':raise RuntimeError('Expected pinned SDK 1.8.0')
        api.connect();gc.collect();gc.disable();reply(dict(ok=True,metadata=api.metadata,source='sdk_fixture_no_device' if a.fixture else 'hardware_sdk',sdk_version='1.8.0',cyclic_gc_deferred=True))
        for line in stream:
            request=json.loads(line);op=request['op'];before=time.monotonic_ns()
            try:
                if op=='read':
                    value=api.sample();value['error_codes']=api.hand.read_joint_error_code().tolist()
                    if a.fixture:value['source']='sdk_fixture_no_device'
                elif op=='write':
                    # Commit only after successful direct SDK call.
                    api.command_joint_targets(request['target_rad']);position_writes+=1;value=dict(issued_target_rad=api.last_target.tolist(),issued_ns=api.last_target_host_ns)
                elif op=='enable':
                    if not a.motion_authorized:raise PermissionError('Motion authorization required')
                    # Set current unloaded posture as target before enabling, avoiding stale firmware target.
                    api.command_joint_targets(api.get_hand_joint_positions())
                    position_writes+=1
                    api.hand.write_joint_enabled(True)
                    value=dict(enable_write_ack=True,enabled_readback=None,control_mode_readback=None,scope='Official 1.8.0 write acknowledged; no enable/mode readback API')
                elif op=='stop':
                    if not a.motion_authorized:raise PermissionError('Motion authorization needed for firmware disable')
                    api.hand.write_joint_enabled(False);reply(dict(ok=True,disable_write_ack=True,disabled_readback=None,scope='SDK disable request acknowledged, physical state unmeasured'));break
                elif op=='close':reply(dict(ok=True,closed=True));break
                else:raise ValueError('Unknown operation')
                reply(dict(ok=True,data=value,sdk_operation_ns=time.monotonic_ns()-before))
            except Exception as e:reply(dict(ok=False,error=type(e).__name__+': '+str(e)))
    except Exception as e:reply(dict(ok=False,error=type(e).__name__+': '+str(e)))
    finally:api.disconnect();stream.close();sock.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fd',type=int,required=True);p.add_argument('--bundle',required=True);p.add_argument('--serial');p.add_argument('--motion-authorized',action='store_true');p.add_argument('--fixture',action='store_true');serve(p.parse_args())
