"""Independent NumPy/SciPy scoring from saved raw local episodes.

Does not import training reward or online metric implementation. Ref remains
the declared reset/takeover pose. No success credit from truncated segments.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def score(path, task, source):
    trace=np.load(path);initial=np.load(source)
    times=trace['time']
    poses=trace['object_rigid_state'][...,:7]
    frame_steps=np.rint(times[:,0]*30).astype(int)
    lower=-.03267458826303482
    reports=[]
    for env in range(poses.shape[1]):
        ref=initial['object_rigid_state'][:7]
        if 'fixed_object_reference' in trace:
            refs=trace['fixed_object_reference'][:,env]
            assert np.max(np.abs(refs-refs[0]))<1e-7, 'Reference must not refresh'
            ref=refs[0]
        obj=poses[:,env]
        dp=np.linalg.norm(obj[:,:3]-ref[:3],axis=-1)
        dr=(Rotation.from_quat(ref[3:]).inv()*Rotation.from_quat(obj[:,3:])).magnitude()
        expected=660 if task=='H' else 600
        complete=bool(frame_steps[-1]>=expected and np.all(np.diff(frame_steps)==1))
        drift=bool(np.max(dp)<.01 and np.max(dr)<.25)
        table=np.zeros(len(times),bool)
        if 'knife_table_contacts' in trace:table=trace['knife_table_contacts'][:,env]>0
        drop=bool(np.any(obj[:,2]<.80) or table.any() or np.any(dp>.1))
        error=[]
        slider=trace['slider'][:,env]
        if task=='S':
            for segment in range(4):
                # Frames142..150 are the first phase's final9 control frames.
                mask=(frame_steps>=segment*150+142)&(frame_steps<=segment*150+150)
                goal=lower+(.04 if segment%2==0 else 0.)
                error.append(float(np.max(np.abs(slider[mask]-goal))) if mask.sum()==9 else None)
            basic=all(e is not None and e<.01 for e in error)
            strict=all(e is not None and e<.002 for e in error)
        else:
            error=[float(np.max(np.abs(slider-float(initial['slider']))))]
            basic=error[0]<.01;strict=error[0]<.002
        bad=np.flatnonzero((dp>=.01)|(dr>=.25))
        reports.append(dict(env=env,complete=complete,world_drift_m=float(dp.max()),world_rotation_rad=float(dr.max()),
            maximum_endpoint_errors_m=error,slider_travel_m=float(np.ptp(slider)),basic_10mm=basic,strict_2mm=strict,
            stable_world_10mm_025rad=drift,drop=drop,success=bool(complete and basic and drift and not drop),
            first_instability_s=float(times[bad[0],env]) if len(bad) else None,
            finger_contact_fraction=np.mean(trace['finger_knife_contacts'][:,env]>0,axis=0).tolist() if 'finger_knife_contacts' in trace else None))
    return dict(source=str(path),reference=str(source),task=task,scope='local reset evidence, not continuous acquisition',episodes=reports)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('trace',type=Path)
    p.add_argument('--task',choices=['H','S'],required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=score(a.trace,a.task,a.source)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


if __name__=='__main__':main()
