"""Summarize all preregistered frozen TABLE tests without case filtering."""
import argparse,collections,hashlib,json
from pathlib import Path
import numpy as np

R=Path(__file__).resolve().parents[1]
D=R/'research/robust-knife-family-20261003'
SPECS=[('independent-core-v1',8,2026100368,'triangular',.1),('independent-capacity-v1',4,2026100369,'pulse',.2),('independent-core-breadth-v1',64,2026100393,'triangular',.1),('independent-capacity-breadth-v1',32,2026100394,'pulse',.2),('independent-height-sensitivity-v1',32,2026100395,'triangular',.1),('independent-fresh-core-v1',128,2026100396,'triangular',.1),('independent-fresh-capacity-v1',64,2026100398,'pulse',.2)]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=D/'independent-validation.json');a=p.parse_args()
    freeze=json.loads((D/'freeze.json').read_text());policy=freeze['policy'];out={'freeze_sha256':sha(D/'freeze.json'),'policy':policy,'conditions':{},'total':0,'complete':0,'scope':'All332 preregistered actual36s TABLE episodes. Same frozen candidate and nominal prior; no training/selection/filtering. Batched contact uses proximity/net-contact proxy, not exact pair force or real robot evidence.'}
    all_geometry={};failures=collections.Counter()
    for name,n,seed,profile,amplitude in SPECS:
        folder=R/'runs/robust-knife-family-20261003/checks'/name;report=json.loads((folder/'report.json').read_text());args=report['args'];rows=[json.loads(x) for x in (folder/'episodes.jsonl').read_text().splitlines()]
        assert len(rows)==n==report['n'];assert args['seed']==seed and args['steps']==1080 and args['load_profile']==profile and args['load_frequency']==2.9 and args['randomization_scale']==1
        assert args['load_max']==amplitude and args['detent_max']==amplitude and args['takeover_seconds']==policy['takeover_seconds']
        assert report['checkpoint_sha256']==policy['sha256'];assert args['checkpoint']==policy['checkpoint_path'];assert not args.get('disable_perturbation')
        assert all(row['control_steps']==1080 for row in rows);counts=collections.Counter(row['failure'] for row in rows if not row['operation_complete']);completed=sum(row['operation_complete'] for row in rows);assert completed==report['completed'];failures.update(counts)
        per_instance={}
        for row in rows:
            sid=row['instance'];item=per_instance.setdefault(sid,{'n':0,'complete':0,'failures':collections.Counter()});item['n']+=1;item['complete']+=int(row['operation_complete'])
            if not row['operation_complete']:item['failures'][row['failure']]+=1
            params=report['physical_asset_parameters'][row['env']];all_geometry[sid]={'handle_size_WTL_m':params['handle_size'],'slider_origin_m':params['slider_origin'],'slider_height_offset_m':params.get('slider_height_offset_m'),'urdf_sha256':params['urdf_sha256']}
        trace=np.load(folder/'trace.npz');initial=np.load(folder/'initial-snapshot.npz');assert trace['slider'].shape==(1080,n)
        condition={'evidence':str(folder.relative_to(R)),'n':n,'complete':completed,'failures':dict(counts),'per_instance':per_instance,'pickup_valid':sum(row['pickup_valid'] for row in rows),'recorded_added_load_abs_peak_N':float(abs(trace['load']).max()),'actual_initial_run_amplitude_range_N':[float(initial['load_amplitude'].min()),float(initial['load_amplitude'].max())],'actual_initial_startup_amplitude_range_N':[float(initial['detent_amplitude'].min()),float(initial['detent_amplitude'].max())],'actual_material_ranges':{'hand':[float(initial['materials'][:,0].min()),float(initial['materials'][:,0].max())],'knife':[float(initial['materials'][:,1].min()),float(initial['materials'][:,1].max())]},'one_step_latency_cases':int(initial['delay'].sum()),'videos':sorted(x.name for x in folder.glob('*.mp4')),'load_peak_scope':'30Hz recorded last-substep engineering added force, not an exhaustive substep maximum or measured real total resistance','report_sha256':sha(folder/'report.json'),'initial_snapshot_sha256':sha(folder/'initial-snapshot.npz'),'trace_sha256':sha(folder/'trace.npz')}
        out['conditions'][name]=condition;out['total']+=n;out['complete']+=completed
    assert out['total']==332;out['failures']=dict(failures);out['physical_geometries']=all_geometry;out['unique_physical_asset_count']=len(all_geometry)
    out['limits']='Four earlier heldouts repeated plus128 fresh sampled bodies and2 nominal-body height variants. Nearby engineering range only; no cross-model/category/real reliability claim. Repeated seeds are not new objects. Failure-priority labels are not chronological onsets. No claim of learned advantage from small development-count differences.'
    a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'output':str(a.output),'total':out['total'],'complete':out['complete'],'failures':out['failures']}))


if __name__=='__main__':main()
