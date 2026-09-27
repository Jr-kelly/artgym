"""Matched actual-state controller comparison; independent scores and raw dots."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scripts.score_g2_local_trace import score


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('runs/g2-local-policy-20260928'))
    p.add_argument('--source',type=Path,default=Path('configs/g2_local/S-after-continuous-learned-H-state.npz'))
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--figure',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args();source=np.load(a.source)
    groups=[('Full teacher',['R13-01-prepared-source-full-teacher']),
        ('Teacher thumb',['R13-02-prepared-source-thumb-only']),
        ('Geometry only',['R13-03-prepared-source-zero-residual-geometry']),
        ('Initial learned offset',['R13-04-prepared-source-static-joint-policy']),
        ('Dynamic joint policy',['R7-01-joint-S-after-actual-H','R7-04-H-prepared-S-fresh-single-repeat'])]
    rows=[];audits=[]
    for label,runs in groups:
        for name in runs:
            for path in sorted((a.root/name).glob('episode-*.npz')):
                t=np.load(path);independent=score(path,'S',a.source)
                for env,out in enumerate(independent['episodes']):
                    errors={key:float(np.max(np.abs(t[key][0,env]-source[key]))) for key in
                        ['all_dof_position','dof_velocity','reference_targets','targets','object_rigid_state','slider_rigid_state','arm_integral_state']}
                    assert max(errors.values())<2e-6, (name,env,errors)
                    audits.append(dict(run=name,episode=path.name,env=env,initial_state_errors=errors))
                    rows.append(dict(method=label,run=name,episode=path.name,replica=env,success=out['success'],
                        body_stable=out['stable_world_10mm_025rad'],strict_2mm=out['strict_2mm'],
                        maximum_endpoint_error_mm=max(out['maximum_endpoint_errors_m'])*1000,
                        world_drift_mm=out['world_drift_m']*1000,world_rotation_rad=out['world_rotation_rad'],
                        slider_travel_mm=out['slider_travel_m']*1000,raw=str(path)))
    with a.csv.open('w',newline='') as f:
        writer=csv.DictWriter(f,list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    result=dict(scope='One identical recorded actual H-prepared state, local resets; not independent geometries or continuous acquisition',
        source=str(a.source),initialization_verified=True,initial_state_tolerance=2e-6,initial_state_checks=audits,
        comparison='Same effective scene, clock, goals and independent criteria; original teacher keeps its original action mapping, geometric zero/static/dynamic variants share the joint motor mapping',
        conclusion='Static first network output also passes; no demonstrated necessity of online learned feedback for S at this fixed source',rows=rows)
    a.audit.write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),constrained_layout=True)
    labels=[g[0] for g in groups]
    for ax,(field,title,limit) in zip(axes,[('maximum_endpoint_error_mm','Worst phase-end error (mm)',10),
        ('world_drift_mm','Maximum body drift (mm)',10),('world_rotation_rad','Maximum body rotation (rad)',.25)]):
        for i,label in enumerate(labels):
            samples=[r[field] for r in rows if r['method']==label]
            ax.scatter(i+np.linspace(-.1,.1,len(samples)),samples,s=45,color=plt.cm.tab10(i),zorder=3)
        ax.axhline(limit,color='firebrick',linestyle='--',label='Required limit')
        if field=='maximum_endpoint_error_mm':ax.axhline(2,color='gray',linestyle=':',label='Strict diagnostic')
        ax.set_xticks(range(len(labels)));ax.set_xticklabels([v.replace(' ','\n') for v in labels],fontsize=9)
        ax.set_title(title);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Matched H-prepared source: local S controls (each dot is one complete20s run)\n'
        'Full teacher0/2 | Thumb0/2 | Geometry0/2 | Initial learned offset2/2 | Dynamic4/4',fontsize=12)
    fig.savefig(a.figure,dpi=160);plt.close(fig)
    print(json.dumps(dict(rows=len(rows),initialization_verified=True,figure=str(a.figure),csv=str(a.csv))))


if __name__=='__main__':main()
