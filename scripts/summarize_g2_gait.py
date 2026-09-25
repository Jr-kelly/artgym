"""Audit completed bounded gait trials, including preflight rejection and aborts."""
import argparse,hashlib,json,csv
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.audit_g2_trajectories import audit


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    old=Path('runs/g2-air-flip-v1/B-sliderdown-pronate180-h30-v2/trace.npz');prefix=np.load(old)
    rows=[]
    for file in sorted(a.root.glob('*-process.json')):
        info=json.loads(file.read_text());name=file.name[:-len('-process.json')];trial=a.root/name
        proc=Path('/proc')/str(info['pid'])/'stat';alive=proc.exists() and proc.read_text().split(') ')[1][0]!='Z'
        if alive:rows.append(dict(name=name,status='running'));continue
        trace=trial/'trace.npz'
        if not trace.exists():trace=trial/'partial-trace.npz'
        row=dict(name=name,status='ended',physical_execution=trace.exists())
        row['command']=info['command']
        manifest=json.loads((Path(info['pin'])/'SOURCE_SHA256.json').read_text())
        for path,sha in manifest.items():
            if hashlib.sha256((Path(info['pin'])/path).read_bytes()).hexdigest()!=sha:raise ValueError('Source pin changed: '+name+'/'+path)
        row['verified_source_files']=len(manifest)
        if trace.exists():
            row.update(audit(trial));t=np.load(trace)
            if 'air_flip' in t['phase']:
                end=np.flatnonzero(t['phase']=='air_flip')[-1]+1
                row['prefix_exact']=bool(end==690 and all(np.array_equal(t[k][:end],prefix[k][:end]) for k in ['q','arm_q','object','wrist','slider','reference_targets']))
                row['flip']=json.loads((trial/'air-flip-check.json').read_text()) if (trial/'air-flip-check.json').exists() else None
            row['slider_target_constant']=bool(np.ptp(t['reference_targets'][:,-1])==0.)
            physics=json.loads((trial/'physics.json').read_text());ids=physics['hand_indices']
            row['hand_command_peak_speed_rad_s']=float(np.abs(np.diff(t['reference_targets'][:,ids],axis=0)).max()*30) if len(t['time'])>1 else 0.
            operation=np.flatnonzero(t['phase']=='operate')
            if len(operation):
                takeover=json.loads((trial/'takeover.json').read_text());reference=np.asarray(takeover['object_world'])
                objects=t['object'][operation]
                dp=np.linalg.norm(objects[:,:3]-reference[:3],axis=1)
                dr=(Rotation.from_quat(reference[3:]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
                unstable=np.flatnonzero((dp>=.01)|(dr>=.25))
                lost=np.flatnonzero((t['finger_knife_contacts'][operation]>0).sum(1)==0)
                row['operation_first_instability']=dict(time_s=float(t['time'][operation[unstable[0]]]),
                    since_takeover_s=float(t['time'][operation[unstable[0]]]-takeover['time']),
                    position_m=float(dp[unstable[0]]),rotation_rad=float(dr[unstable[0]])) if len(unstable) else None
                row['operation_first_all_finger_contact_loss_s']=float(t['time'][operation[lost[0]]]) if len(lost) else None
                row['policy_first_command_delta_rad']=float(np.abs(t['reference_targets'][operation[0],ids]-takeover['targets']).max())
            if (trial/'gait-checks.json').exists():
                checks=json.loads((trial/'gait-checks.json').read_text());row['gait_stages']=checks['stages']
                plan=json.loads((trial/'gait-plan.json').read_text())
                previous_moving=[]
                motor_names=['index','middle','pinky','ring','thumb'];contact_names=['thumb','index','middle','ring','pinky']
                for stage,definition in zip(row['gait_stages'],plan['stages']):
                    moving=definition.get('moving_indices',[])
                    if moving:previous_moving=moving
                    required=definition.get('require_no_contact')
                    # Earlier pins omitted an explicit release gate. The requested
                    # unload still requires actual absence, not only stable holding.
                    if required is None and stage['name'].endswith('unloaded_hold') and len(previous_moving)==4:
                        required=contact_names.index(motor_names[previous_moving[0]//4])
                    fractions=stage['contact_fraction_thumb_index_middle_ring_pinky']
                    gate=required is None or fractions[required]==0.
                    if definition.get('require_contact') is not None:gate=gate and fractions[definition['require_contact']]>=.9
                    stage['requested_contact_condition_met']=bool(gate)
                    stage['stage_completed']=bool(stage['stable'] and gate)
                row['first_instability_time_s']=next((v['first_instability_time_s'] for v in checks['stages'] if v['first_instability_time_s'] is not None),None)
            # Actual contact locations on the knife surface, in that link's local frame.
            contacts=trial/'knife-contact-pairs.jsonl';at_end=[]
            if contacts.exists():
                for line in contacts.read_text().splitlines():
                    v=json.loads(line)
                    if v['step']<len(t['time'])-30:continue
                    for side in [0,1]:
                        if v['body'+str(side)] in ['link_0','link_1'] and 'localPos'+str(side) in v:
                            at_end.append(dict(step=v['step'],knife_link=v['body'+str(side)],other_link=v['body'+str(1-side)],
                                position_in_knife_link=v['localPos'+str(side)],normal=v['normal'],solver_lambda=v['lambda_value']))
            row['last_second_actual_contact_locations']=at_end
        else:row['stage']='pre_physics_failure'
        if (trial/'failure.json').exists():row['abort']=json.loads((trial/'failure.json').read_text())
        if (trial/'report.json').exists():
            report=json.loads((trial/'report.json').read_text());row['score']=report
        rows.append(row)
    result=dict(trials=rows,launches=len(rows),physical_executions=sum(v.get('physical_execution',False) for v in rows),
        no_new_training=True,scope='Development trials; A only measures endpoint operation. Prefix and gait success never substitute for continuous B/C success.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(name=v['name'],physical=v.get('physical_execution'),status=v['status'],prefix=v.get('prefix_exact'),
        phase=v.get('abort',{}).get('last_phase'),operations=v.get('operation_steps'),whole=v.get('whole_success'),
        stages=[(s['name'],s['stable']) for s in v.get('gait_stages',[])]) for v in rows]))


if __name__=='__main__':main()
