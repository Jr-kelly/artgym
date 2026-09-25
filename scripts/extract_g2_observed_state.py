"""Export measured planning geometry with fresh trace provenance, never reset a sim."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--phase',required=True)
    p.add_argument('--template',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve old geometry')
    path=a.trial/'trace.npz'
    if not path.exists():path=a.trial/'partial-trace.npz'
    t=np.load(path);i=int(np.flatnonzero(t['phase']==a.phase)[-1]);d=json.loads(a.template.read_text());physics=json.loads((a.trial/'physics.json').read_text())
    obj=transform(t['object'][i,:3],t['object'][i,3:]);wrist=transform(t['wrist'][i,:3],t['wrist'][i,3:]);relative=np.linalg.inv(obj)@wrist
    d.update(touch_q=t['q'][i].tolist(),close_q=t['reference_targets'][i,physics['hand_indices']].tolist(),wrist_in_knife=relative.tolist(),
        source_trial=str(a.trial),source_trace=str(path),source_step=i,source_phase=str(t['phase'][i]),source_time_s=float(t['time'][i]),
        source_trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),planning_template=str(a.template),
        scope='Actual physically executed state exported for planning only; not a continuous-run state reset.')
    pairs=[json.loads(s) for s in (a.trial/'knife-contact-pairs.jsonl').read_text().splitlines()];normals=[];sources=[]
    for j,finger in enumerate(['thumb','index','middle','ring','pinky']):
        values=[]
        for row in pairs:
            if row['step']!=i:continue
            for side in [0,1]:
                if '_'+finger+'_' in row['body'+str(side)] and row['body'+str(1-side)]=='link_0':
                    values.append(obj[:3,:3].T@np.asarray(row['normal'])*(1 if side==0 else -1))
        if values:
            n=np.mean(values,axis=0);n/=np.linalg.norm(n);normals.append(n.tolist());sources.append('actual current link_0 contacts')
        else:
            normals.append(d.get('contact_normals',[[1,0,0]]*5)[j]);sources.append('planning-template normal; no actual body contact in this frame')
    d['contact_normals']=normals;d['contact_normal_sources']=sources
    a.output.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),step=i,time_s=d['source_time_s'],phase=a.phase,sha256=d['source_trace_sha256'])))


if __name__=='__main__':main()
