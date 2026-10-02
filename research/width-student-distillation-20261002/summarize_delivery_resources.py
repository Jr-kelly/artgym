"""Actual allocated GPU intervals and measured utilization, never budget estimates."""
import collections,datetime,json
from scripts.record_wuji_width_goal import R,D,record

def dt(s):return datetime.datetime.fromisoformat(s)

def main():
    jobs=[]
    for p in (R/'runs/width-student-distillation-20261002/jobs').glob('*/result.json'):
        j=json.loads(p.read_text());cmd=j['command']
        category='precheck'
        if '--video' in cmd:category='rendered_video'
        elif 'scripts.static_wuji_geometry' in cmd:category='static_data'
        elif 'scripts.train_wuji_unified_student' in cmd:category='discarded_updates' if j.get('disposable_precheck',False) else 'formal_training'
        elif 'scripts.evaluate_wuji_geometry' in cmd:category='evaluation_'+str(j.get('reserved_phase') or 'dev')
        j['category']=category;jobs.append(j)
    assert jobs;unknown=[j for j in jobs if j.get('remote_status_unknown',False)]
    markers=[]
    for j in jobs:
        markers.extend([(dt(j['start_utc']),1,j['gpu_uuid']),(dt(j['end_utc']),-1,j['gpu_uuid'])])
    active=set();peak=0
    for timestamp,delta,device in sorted(markers,key=lambda r:(r[0],r[1])):
        if delta==1:assert device not in active;active.add(device)
        else:assert device in active;active.remove(device)
        peak=max(peak,len(active))
    assert peak<=8 and not active
    categories=collections.defaultdict(lambda:dict(jobs=0,gpu_hours=0,failed_jobs=0))
    devices=collections.defaultdict(lambda:dict(jobs=0,gpu_hours=0))
    for j in jobs:
        c=categories[j['category']];c['jobs']+=1;c['gpu_hours']+=j['gpu_hours'];c['failed_jobs']+=int(j['exit_code']!=0)
        d=devices[j['device']];d['jobs']+=1;d['gpu_hours']+=j['gpu_hours']
    samples=[json.loads(l) for l in (D/'UTILIZATION_SAMPLES.jsonl').read_text().splitlines()]
    valid=[s for s in samples if s.get('verified')];assert valid
    end=dt(valid[-1]['utc']);start=end-datetime.timedelta(hours=4);covered=0;area=0;allcovered=0;allarea=0
    for x,y in zip(valid,valid[1:]):
        a=dt(x['utc']);b=dt(y['utc']);seconds=(b-a).total_seconds()
        if seconds>90 or seconds<=0:continue
        mean=(x['whole_machine_utilization_pct']+y['whole_machine_utilization_pct'])/2
        allcovered+=seconds;allarea+=seconds*mean
        overlap=max(0,(min(b,end)-max(a,start)).total_seconds())
        covered+=overlap;area+=overlap*mean
    s=json.loads((D/'STATE.json').read_text());new=sum(j['gpu_hours'] for j in jobs);total=s['historical_gpu_hours']+new
    result=dict(known_new_gpu_hours=sum(j['gpu_hours'] for j in jobs if not j.get('remote_status_unknown',False)),unreconciled_gpu_hours_charge=sum(j['gpu_hours'] for j in unknown),unreconciled_remote_jobs=[j['name'] for j in unknown],budget_not_actual_until_receipts_reconciled=bool(unknown),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),historical_gpu_hours=s['historical_gpu_hours'],new_gpu_hours=new,cumulative_gpu_hours=total,remaining_gpu_hours=64-total,max_gpu_hours=64,peak_combined_gpus=peak,completed_jobs=len(jobs)-len(unknown),accounted_jobs=len(jobs),unreconciled_jobs=len(unknown),known_cumulative_gpu_hours=s['historical_gpu_hours']+sum(j['gpu_hours'] for j in jobs if not j.get('remote_status_unknown',False)),categories=dict(categories),devices=dict(devices),failed_jobs=[dict(name=j['name'],exit_code=j['exit_code'],gpu_hours=j['gpu_hours'],category=j['category']) for j in jobs if j['exit_code']],formal_updates=s['optimizer_updates'],formal_transitions=s['optimizer_updates']*1024,discarded_updates=s['disposable_optimizer_updates'],discarded_transitions=s['disposable_interactions'],wall_seconds_since_goal_start=(datetime.datetime.now(datetime.timezone.utc)-dt(s['start_utc'])).total_seconds(),gpu_job_span_seconds=(max(dt(j['end_utc']) for j in jobs)-min(dt(j['start_utc']) for j in jobs)).total_seconds(),utilization=dict(first_observed_utc=valid[0]['utc'],last_observed_utc=valid[-1]['utc'],valid_samples=len(valid),covered_seconds=allcovered,observed_time_weighted_whole_machine_mean_pct=allarea/allcovered,four_hour_window_end_utc=valid[-1]['utc'],last_four_hours_observed_seconds=covered,last_four_hours_unobserved_assumed_zero_estimate_pct=area/14400,method='30s NVML snapshots, trapezoidal estimate only for adjacent gaps<=90s; unobserved gaps countzero in four-hour estimate. This is not the Ska service utilization telemetry or a continuous measurement certificate.',threshold_pct=26,target_pct=40))
    assert total<=64 and s['optimizer_updates']==12800
    (D/'FINAL_RESOURCES.json').write_text(json.dumps(result,indent=2)+'\n')
    record('actual_resource_and_global_concurrency_audit_complete',evidence='research/width-student-distillation-20261002/FINAL_RESOURCES.json',next='Stop verified own utilization process; preserve unrelated user processes and report actual consumption')

if __name__=='__main__':main()
