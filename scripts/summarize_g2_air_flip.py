"""Read-only phase and provenance audit for the no-table-regrasp route."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.audit_g2_trajectories import audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    rows=[];traces={}
    for process in sorted(args.root.glob('*-process.json')):
        info=json.loads(process.read_text());name=process.name[:-len('-process.json')];trial=args.root/name
        file=trial/'trace.npz'
        if not file.exists():file=trial/'partial-trace.npz'
        if not file.exists():continue
        trace=np.load(file);traces[name]=trace
        row=audit(trial);row['trace_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
        pin=Path(info['pin']);manifest=json.loads((pin/'SOURCE_SHA256.json').read_text())
        bad=[key for key,sha in manifest.items() if hashlib.sha256((pin/key).read_bytes()).hexdigest()!=sha]
        if bad:raise ValueError('Source pin changed: '+str(bad))
        row['verified_source_files']=len(manifest)
        command=info['command'];row['initial_face']='down' if '--slider-face' in command and command[command.index('--slider-face')+1]=='down' else 'up'
        row['table_supported_regrasp']=bool('--table-supported-seat' in command)
        if row['table_supported_regrasp']:raise ValueError('Table-supported regrasp forbidden in air-flip route')
        row['slider_motor_target_constant']=bool(np.ptp(trace['reference_targets'][:,-1])==0.)
        if not row['slider_motor_target_constant']:raise ValueError('Slider motor target changed')
        settle=np.flatnonzero(trace['phase']=='table_settle')
        flip=np.flatnonzero(trace['phase']=='air_flip')
        row['initial_slider_face_up_component']=float(Rotation.from_quat(trace['object'][settle[-1],3:]).as_matrix()[2,1]) if len(settle) else None
        check=trial/'air-flip-check.json'
        row['flip']=json.loads(check.read_text()) if check.exists() else None
        if len(flip):row['final_slider_face_up_component']=float(Rotation.from_quat(trace['object'][flip[-1],3:]).as_matrix()[2,1])
        seat=np.flatnonzero(trace['phase']=='seat')
        if len(seat):
            obj=trace['object'][seat];r0=Rotation.from_quat(obj[0,3:]);angle=(r0.inv()*Rotation.from_quat(obj[:,3:])).magnitude()
            drift=np.linalg.norm(obj[:,:3]-obj[0,:3],axis=1)
            escaped=np.flatnonzero((drift>.01)|(angle>.25))
            row['seating']=dict(frames=len(seat),max_world_drift_m=float(drift.max()),max_world_rotation_rad=float(angle.max()),
                first_10mm_or_025rad_departure_s=float(trace['time'][seat[escaped[0]]]-trace['time'][seat[0]]) if len(escaped) else None,
                interpretation='Diagnostic drift from seating-start object reference, not a unique causal explanation or an operation metric.')
        rows.append(row)
    paired=[]
    reference='B-sliderdown-pronate180-h30-v2'
    if reference in traces:
        a=traces[reference];end=int(np.flatnonzero(a['phase']=='air_flip')[-1])+1
        for name,b in traces.items():
            if name==reference or len(b['time'])<end:continue
            if next(r['initial_face'] for r in rows if r['name']==name)!='down':continue
            fields=['q','arm_q','object','wrist','slider','targets','finger_knife_contacts']
            equality={key:bool(np.array_equal(a[key][:end],b[key][:end])) for key in fields}
            paired.append(dict(reference=reference,trial=name,frames=end,equal=equality,all_equal=all(equality.values())))
    result=dict(trials=rows,prefix_comparisons=paired,
        scope='Development diagnostics. Up-face v1 is retained as a control. No variation success rate or policy success is inferred from pickup/flip.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(trials=len(rows),prefix_equal=[r['all_equal'] for r in paired],output=str(args.output))))


if __name__=='__main__':main()
