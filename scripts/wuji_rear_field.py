"""One field configuration/launcher; stdlib checks do not import training packages."""
import argparse, csv, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUNDLE='research/rear-sim2real-20261009/bundle-deploy-v10.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_config(path):
    c=json.loads(Path(path).read_text())
    if c.get('format')!='wuji-rear-field-v1':raise ValueError('Unknown field configuration')
    return c
def resolved(c):
    for k in ['bundle','calibration','initial_estimate']:
        if c.get(k):c[k]=str((ROOT/c[k]).resolve())
    for k in ['inference_python','sdk_python']:
        # Preserve venv launcher symlink: resolving bin/python to /usr/bin loses pyvenv.cfg.
        if c.get(k):c[k]=os.path.abspath(os.path.expandvars(os.path.expanduser(c[k])))
    return c
def require_g2(c):
    if (c or {}).get('execution',{}).get('backend')=='corobot-unified-v1':
        from scripts.wuji_rear_network_backend import network_config
        return network_config(c)
    from scripts.wuji_rear_g2_guard import bridge_config
    return bridge_config(c)
def estimates(spec,c):
    import numpy as np
    e=c.get('initial_estimate')
    if not e:return spec
    x=json.loads(Path(e).read_text())
    if x.get('format')!='wuji-rear-initial-estimate-v1' or x.get('frame')!='knife_body_initial' or x.get('unit')!='mm' or not x.get('source'):raise ValueError('Initial estimate needs knife_body_initial, mm and source')
    if x.get('grasp')!='rear-fixed-wrist-v1':raise ValueError('Initial estimate belongs to another grasp')
    delta=np.asarray(x['translation_mm'],dtype=float)
    edge=float(x['slider_near_edge_mm'])
    if delta.shape!=(3,) or not np.isfinite(delta).all() or not np.isfinite(edge) or not 0<=edge<=112:raise ValueError('Invalid placement/slider dimensions')
    spec=dict(spec)
    o=np.array(spec['object_initial_estimate']);s=np.array(spec['slider_initial_estimate']);v=o[:3,:3]@(delta/1000)
    o[:3,3]+=v;s[:3,3]+=v+o[:3,2]*((edge-30)/1000)
    spec['object_initial_estimate']=o.tolist();spec['slider_initial_estimate']=s.tolist()
    spec['field_initial_estimate']=dict(x,path=str(e),sha256=sha(e),accuracy='Unmeasured manual prior; not runtime vision or simulation truth')
    return spec

def envcheck(c):
    c=resolved(c);out=dict(root=str(ROOT),resolved=c,inference=None,sdk=None,dependencies=None,g2='field_bridge_or_facts_not_configured',real_robot_ran=False)
    if c.get('g2',{}).get('backend')=='corobot-local-v1':
        require_g2(c);out['g2']='private_bridge_pinned_awaiting_actual_connection_and_field_evidence'
    network=c.get('execution',{}).get('backend')=='corobot-unified-v1'
    if network:
        require_g2(c);out['g2']='unified_network_executor_pinned_awaiting_actual_field_readback'
    for key,code in [('sdk',"import json,sys,wujihandpy,numpy;from scripts.wuji_rear_sdk_worker import usb_inventory;print(json.dumps(dict(python=sys.version,executable=sys.executable,sdk=wujihandpy.__version__,numpy=numpy.__version__,usb=usb_inventory(),mode_readback=hasattr(wujihandpy.Hand,'read_joint_control_mode'),enable_readback=hasattr(wujihandpy.Hand,'read_joint_enabled'))))"),('inference',"import isaacgym;import json,sys,torch,numpy,scipy,hydra,omegaconf,gym;from scripts.wuji_rear_controller import RearController;print(json.dumps(dict(python=sys.version,executable=sys.executable,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.is_available(),numpy=numpy.__version__,scipy=scipy.__version__,isaacgym=isaacgym.__file__)))")]:
        if network and key=='sdk':
            code="import json,sys,numpy,importlib.metadata;from corobot_client_cpp.remote_env_client import RemoteEnvClient;print(json.dumps(dict(python=sys.version,numpy=numpy.__version__,corobot=importlib.metadata.version('corobot-client-cpp'),local_usb_required=False,connect_called=False)))"
        exe=c['execution']['backend_python'] if network and key=='sdk' else c.get(key+'_python')
        if not exe:out[key]=dict(ok=False,error='Set '+key+'_python in field config');continue
        env=dict(os.environ,PYTHONPATH=str(ROOT)+':'+str(ROOT/'rl_games'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PATH=str(Path(exe).parent)+':'+os.environ.get('PATH',''))
        if key=='sdk':env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
        else:env['LD_LIBRARY_PATH']=str(Path(exe).parent.parent/'lib')
        try:
            r=subprocess.run([exe,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
            out[key]=dict(ok=r.returncode==0,stdout=r.stdout,stderr=r.stderr)
        except (OSError,subprocess.TimeoutExpired) as e:out[key]=dict(ok=False,error=str(e))
    try:
        spec=json.loads(Path(c['bundle']).read_text());bad=[]
        for n,h in spec['required_sha256'].items():
            p=ROOT/n
            if not p.is_file() or sha(p)!=h:bad.append(n)
        out['dependencies']=dict(ok=not bad,count=len(spec['required_sha256']),missing_or_changed=bad,bundle_sha256=sha(c['bundle']))
    except Exception as e:out['dependencies']=dict(ok=False,error=str(e))
    out['usb_access']=[]
    for p in ([] if network else Path('/sys/bus/usb/devices').glob('*/idVendor')):
        if p.read_text().strip()!='0483':continue
        base=p.parent
        if (base/'idProduct').read_text().strip()!='2000':continue
        dev=Path('/dev/bus/usb')/('%03d'%int((base/'busnum').read_text()))/('%03d'%int((base/'devnum').read_text()))
        out['usb_access'].append(dict(path=str(dev),read=os.access(dev,os.R_OK),write=os.access(dev,os.W_OK)))
    return out

def targets(c):
    import numpy as np
    from scripts.g2_kinematics import G2Kinematics
    from isaacgymenvs.deploy.wuji.joint_mapping import SDK_NAMES
    c=resolved(c);s=json.loads(Path(c['bundle']).read_text());k=G2Kinematics();q=np.asarray(s['arm_q_rad']);frames=k.forward(q,True)
    profile=json.loads(Path(c['calibration']).read_text()) if c.get('calibration') else {}
    network=c.get('execution',{}).get('backend')=='corobot-unified-v1' and bool(c.get('execution',{}).get('profile'))
    network_profile=json.loads(Path(c['execution']['profile']).read_text()) if network else None
    if network:require_g2(c);profile=network_profile['hand']
    signs=profile.get('model_from_device_sign',[1]*20);zero=profile.get('device_zero_rad',[0]*20)
    arm=[dict(model_name=n,target_rad=float(v),target_degree=float(np.degrees(v)),model_lower_rad=float(k.lower[i]),model_upper_rad=float(k.upper[i]),sdk_name_or_id=None,hardware_sendable=False) for i,(n,v) in enumerate(zip(k.names,q))]
    hand=[]
    for i,n in enumerate(s['runtime_joint_names']):
        slot=SDK_NAMES.index(n);sign=signs[i];z=zero[i]
        hand.append(dict(model_name=n,model_index=i,sdk_name=n,sdk_finger_index=slot//4,sdk_joint_index=slot%4,unit='rad',sign=sign,device_zero_rad=z,model_lower_rad=s['model_lower_rad'][i],model_upper_rad=s['model_upper_rad'][i],device_lower_rad=profile.get('device_lower_rad',[None]*20)[i],device_upper_rad=profile.get('device_upper_rad',[None]*20)[i],open_model_rad=s['open_q_rad'][i],hold_motor_model_rad=s['hold_target_rad'][i],open_device_rad=sign*s['open_q_rad'][i]+z,hold_motor_device_rad=sign*s['hold_target_rad'][i]+z,actual_q=None,axes_verified=profile.get('axes_verified',False),absolute_zero_verified=profile.get('absolute_zero_verified',False)))
    if network:
        arm_signs=network_profile['model_from_device_sign'];arm_zero=network_profile['device_zero_rad']
        for i,row in enumerate(arm):
            row.update(hardware_sendable=True,interface='right_arm JOINT_ABS',device_target_rad=arm_signs[i]*float(q[i])+arm_zero[i],sdk_name_or_id='verified_right_arm_slot_'+str(i))
        for i,row in enumerate(hand):
            row.update(interface='right_effector absolute position',action_slot=profile['action_names'].index(row['model_name']),state_slot=profile['state_indices'][profile['state_names'].index(row['model_name'])],mapping_source='Pinned network field profile; no direct USB driver')
    fixed=[]
    for name,origin,index,axis in k.chain:
        if index is None:fixed.append(dict(child_frame=name,parent_to_child=origin.tolist(),assumption='Locked non-right-arm joints and mounting in supplied simulation URDF; physical value unverified'))
    from scipy.spatial.transform import Rotation
    fk=frames['hand_r_base_link'];prior=np.asarray(s['wrist_world']);reserve=s.get('issued_limit_reserve_rad',0)
    for i,row in enumerate(hand):
        row['nominal_reserved_hold_model_rad']=float(np.clip(s['hold_target_rad'][i],s['model_lower_rad'][i]+reserve,s['model_upper_rad'][i]-reserve))
        row['nominal_hold_clip_rad']=row['nominal_reserved_hold_model_rad']-row['hold_motor_model_rad']
        row['nominal_reserved_hold_device_rad']=row['sign']*row['nominal_reserved_hold_model_rad']+row['device_zero_rad']
    return dict(format='wuji-rear-named-targets-v1',bundle_sha256=sha(c['bundle']),arm=arm,hand=hand,command_target_model_base_to_hand=fk.tolist(),saved_policy_prior_wrist=prior.tolist(),prior_source='Recorded finite-actuator simulation orientation; not command-target FK or hardware measurement',target_fk_vs_saved_prior=dict(position_delta_m=(fk[:3,3]-prior[:3,3]).tolist(),rotation_delta_rad=float(Rotation.from_matrix(fk[:3,:3].T@prior[:3,:3]).magnitude())),fixed_chain=fixed,command_target_gravity_in_hand=(fk[:3,:3].T@np.array([0,0,-1.])).tolist(),policy_prior_gravity_in_hand=(prior[:3,:3].T@np.array([0,0,-1.])).tolist(),hardware_base_to_model_base=None,hardware_flange_to_hand=None,real_g2_state=None,network_mapping_verified=network,scope='Model targets, not measured pose. G2 numeric IDs are not SDK indices. Hand hold motor targets include preload; nominal reserve/clipping shown separately.')

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['configure','envcheck','targets','estimate','run']);p.add_argument('--config',type=Path,default=Path('field.json'));p.add_argument('--inference-python');p.add_argument('--sdk-python');p.add_argument('--legacy-usb',action='store_true');p.add_argument('--serial');p.add_argument('--calibration');p.add_argument('--initial-estimate');p.add_argument('--output',type=Path);p.add_argument('--offset-mm',type=float,nargs=3,default=[0,0,0]);p.add_argument('--slider-edge-mm',type=float,default=30);p.add_argument('--source',default='manual_ruler_alignment_unmeasured')
    argv=sys.argv[1:];child_index=None
    if argv and argv[0]=='run':
        child_modes={'sim','discover','read','check','enable','hold','response','probe','push','session','stop'}
        child_index=next((i for i,v in enumerate(argv[1:],1) if v in child_modes),None)
    if child_index is None:a,extra=p.parse_known_args(argv)
    else:a=p.parse_args(argv[:child_index]);extra=argv[child_index:]
    if a.mode=='configure':
        if a.config.exists():raise FileExistsError(a.config)
        c=dict(format='wuji-rear-field-v1',bundle=BUNDLE,inference_python=a.inference_python,sdk_python=a.sdk_python,serial=a.serial,calibration=a.calibration,initial_estimate=a.initial_estimate,topology='Wuji USB and both Python processes on the same field Linux PC; G2 controller on local manufacturer connection; no public-network policy stream',wuji=dict(position_mode_verified=False,position_mode_source=None,hardware_max_joint_speed_rad_s=[None]*20,speed_source=None),g2=dict(status='blocked',asset_model_clue='G2_t2_crsB',exact_hardware_model=None,official_controller_example=None,field_pc=None,read_only_state_example=None,mounting_source=None))
        if not a.legacy_usb:
            c['topology']='Wuji on robot body; field PC uses one unified network executor for arm and hand'
            c['sdk_python']=None;c['execution']=dict(backend='corobot-unified-v1',backend_python=None,backend_script=None,profile=None,source_sha256={},profile_sha256=None)
        a.config.write_text(json.dumps(c,indent=2));print(a.config);return
    if a.mode=='estimate':
        if not a.output:raise ValueError('--output required')
        if a.output.exists():raise FileExistsError(a.output)
        v=dict(format='wuji-rear-initial-estimate-v1',frame='knife_body_initial',unit='mm',grasp='rear-fixed-wrist-v1',translation_mm=a.offset_mm,slider_near_edge_mm=a.slider_edge_mm,source=a.source,accuracy='Manual prior; field alignment error unmeasured',axes='x across 19mm width, y outward slider face, z tail to tip',wrist_source='Saved simulation orientation until measured G2 mounting/FK verified')
        a.output.write_text(json.dumps(v,indent=2));print(a.output);return
    c=resolved(read_config(a.config))
    if a.mode=='run':
        if not extra:raise ValueError('run requires implemented mode e.g. discover/read/session')
        mode=extra[0];fixture='--fixture' in extra
        if mode in ['session','hold','response','probe','push'] and not fixture:require_g2(c)
        network=c.get('execution',{}).get('backend')=='corobot-unified-v1'
        if network and mode=='discover':raise ValueError('Use the private read-only network capture command; USB discover is not this topology')
        exe=(c['execution']['backend_python'] if network else c['sdk_python']) if mode in ['discover','read','check','stop','enable'] else c['inference_python']
        if not exe:raise ValueError('Python path missing in field configuration')
        args=extra+['--bundle',c['bundle'],'--field-config',str(a.config.resolve())]
        if not network:args+=['--sdk-python',c['sdk_python']]
        if c.get('serial'):args+=['--serial',c['serial']]
        if c.get('calibration'):args+=['--calibration',c['calibration']]
        env=dict(os.environ,PYTHONPATH=str(ROOT)+':'+str(ROOT/'rl_games'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PATH=str(Path(exe).parent)+':'+os.environ.get('PATH',''))
        if exe==(c['execution']['backend_python'] if network else c['sdk_python']):env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
        else:env['LD_LIBRARY_PATH']=str(Path(exe).parent.parent/'lib')
        os.chdir(ROOT);os.execve(exe,[exe,'-m','scripts.run_wuji_rear']+args,env)
    value=envcheck(c) if a.mode=='envcheck' else targets(c)
    body=json.dumps(value,indent=2)
    if a.output:a.output.write_text(body)
    print(body)
    if a.mode=='envcheck' and not all(value[k]['ok'] for k in ['inference','sdk','dependencies']):raise SystemExit(2)
if __name__=='__main__':main()
