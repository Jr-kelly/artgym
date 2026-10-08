"""Position response diagnostics, preserving read/write timestamps and coarse sampling limits.
No force or stiffness inference from encoder signals. Simulation and fixture are named explicitly.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np

def lag_scan(t,issued_t,issued,q,baseline_bias,local=True,reasons=()):
    dt=float(np.median(np.diff(t)));candidates=[]
    # A command issued at the read timestamp occurs after that read. No interpolation.
    for k in range(-2,7):
        index=np.searchsorted(issued_t,t-k*dt-1e-9,side='right')-1
        valid=(index>=0)&(index<len(issued))
        x=issued[np.clip(index,0,len(issued)-1)];x=x-x[valid][0]
        y=q-q[valid][0];dynamic=valid&(np.abs(x)>max(.0001,.05*np.ptp(x[valid])))
        if dynamic.sum()<12:continue
        xx=x[dynamic];yy=y[dynamic];design=np.c_[xx,np.ones(len(xx))];gain,offset=np.linalg.lstsq(design,yy,rcond=None)[0];error=yy-gain*xx-offset
        candidates.append(dict(lag_samples=k,lag_ms=k*dt*1000,shape_fit_rmse_rad=float(np.sqrt(np.mean(error**2))),amplitude_gain=float(gain)))
    why=list(reasons)
    if not local:why.append('Closed-loop task: feedback and changing contact confound mechanical lag; not a single-joint identification excitation')
    if np.ptp(issued)<.003 or np.ptp(q)<.0005:why.append('Insufficient issued or encoder excitation')
    local_index=np.searchsorted(issued_t,t-1e-9,side='right')-1
    local_u=issued[np.maximum(local_index,0)];delta=np.diff(local_u);sign=np.sign(delta[np.abs(delta)>max(1e-6,np.ptp(local_u)*1e-4)])
    reversals=int(np.count_nonzero(np.diff(sign)))
    if local and reversals<2:why.append('Only one slow excursion; no independent temporal features/repetition to establish lag repeatability under loaded contact')
    if np.std(np.diff(t))/dt>.2:why.append('Irregular sampling: no reliable sample-grid lag estimate')
    if len(candidates)<3:why.append('Insufficient usable window')
    best=min(candidates,key=lambda r:r['shape_fit_rmse_rad']) if candidates else None
    if best:
        floor=max(2e-5,best['shape_fit_rmse_rad']*.15)
        nearby=[r['lag_samples'] for r in candidates if r['shape_fit_rmse_rad']<=best['shape_fit_rmse_rad']+floor]
        if len(nearby)>1:why.append('Several integer-sample lags fit within residual/noise tolerance: '+str(nearby))
        if best['lag_samples']<0:why.append('Best fit implies encoder leads command: waveform/contact/alignment cannot support causal lag')
        if best['shape_fit_rmse_rad']>max(.0002,.1*np.ptp(q)):why.append('Waveform mismatch too large for a scalar delayed position response')
    reliable=best is not None and not why
    return dict(status='coarse_position_lag_supported' if reliable else 'unable_to_reliably_estimate',reasons=why,sampling_period_ms=dt*1000,window_s=[float(t[0]),float(t[-1])],estimate_samples=best['lag_samples'] if reliable else None,estimate_ms=best['lag_ms'] if reliable else None,resolution_ms=dt*1000,credible_sampling_bin_ms=[max(0,(best['lag_samples']-1)*dt*1000),(best['lag_samples']+1)*dt*1000] if reliable else None,bin_scope='Conservative one-sampling-period neighborhood, not statistical or system identification confidence interval',descriptive_best_fit=best,candidates=candidates,scope='Integer sample shift, no interpolation or sub-sample millisecond precision; amplitude gain is not stiffness')

def load(folder,joint,phase=None):
    folder=Path(folder);sim=(folder/'commands.jsonl').exists();path=folder/('commands.jsonl' if sim else 'control.jsonl')
    rows=[json.loads(l) for l in path.read_text().splitlines() if l.strip()];rows=[r for r in rows if 'measured_q_rad' in r or 'encoder_model_rad' in r]
    phases={r['phase'] for r in rows};phase=phase or ('loaded_local_response' if 'loaded_local_response' in phases else 'push_hold' if 'push_hold' in phases else 'closed_loop_push_and_hold')
    timing={r['cycle_id']:r for r in [json.loads(l) for l in (folder/'timing.jsonl').read_text().splitlines()]} if (folder/'timing.jsonl').exists() else {}
    data=[]
    for n,r in enumerate(rows):
        raw_time=r.get('time_s',r.get('elapsed_s'))
        read_ns=r.get('host_read_sample_ns');write=(r.get('write_timing') or {}).get('host_ack_ns')
        read_time=raw_time if read_ns is None else read_ns/1e9;issue_time=raw_time if write is None else write/1e9
        u=r.get('issued_target_rad');q=r.get('measured_q_rad',r.get('encoder_model_rad'))
        if u is None:continue
        tm=timing.get(r.get('cycle_id'),{})
        data.append(dict(row=n,phase=r['phase'],t=read_time,ut=issue_time,q=q[joint],u=u[joint],raw_time=raw_time,read_ns=read_ns,write_ns=write,complete_ms=tm.get('end_to_end_ms',r.get('end_to_end_ms',r.get('loop_ms'))),compute_ms=r.get('host_compute_ms'),read_ipc_ms=(r.get('read_timing') or {}).get('host_ipc_roundtrip_ms'),write_ipc_ms=(r.get('write_timing') or {}).get('host_ipc_roundtrip_ms'),read_sdk_ms=(r.get('read_timing') or {}).get('sdk_operation_ms'),write_sdk_ms=(r.get('write_timing') or {}).get('sdk_operation_ms'),record_ms=tm.get('record_ms')))
    a={k:np.array([d[k] for d in data]) for k in ['t','ut','q','u']};selected=np.array([d['phase']==phase for d in data]);assert selected.sum()>=30,'At least 30 selected samples required'
    idx=np.searchsorted(a['ut'],a['t']-1e-9,side='right')-1;valid=idx>=0;aligned=a['u'][np.maximum(idx,0)]
    start=a['t'][np.flatnonzero(selected)[0]];baseline=valid&(a['t']>=start-.9)&(a['t']<start)
    if phase=='loaded_local_response':baseline=selected&valid&(a['t']<start+.9)
    reasons=[]
    if baseline.sum()<10:baseline=selected&valid&(a['t']<start+.3);reasons.append('No long static baseline; task-start bias proxy only')
    bias=float(np.median((aligned-a['q'])[baseline]));recovery=selected&(a['t']>a['t'][selected][-1]-.8);drift=float(np.median((aligned-a['q'])[recovery])-bias)
    if phase=='loaded_local_response' and abs(drift)>.0005:reasons.append('Static loaded offset changed by >0.5mrad: contact/load or hysteresis not constant')
    if not sim and data[0]['read_ns'] is None:reasons.append('Legacy elapsed timestamps lack precise read/issue alignment')
    contact=None
    if sim and (folder/'trace.npz').exists():
        tr=np.load(folder/'trace.npz');mask=(tr['time']>=start)&(tr['time']<=a['t'][selected][-1]+1/30);contact=dict(thumb_fraction=float(tr['thumb'][mask].mean()),support_fraction=float(tr['support'][mask].mean()))
        if contact['thumb_fraction']<.95 or contact['support_fraction']<.95:reasons.append('Simulation shows changing/lost contact in analysis window')
    local=phase=='loaded_local_response';lag=lag_scan(a['t'][selected],a['ut'],a['u'],a['q'][selected],bias,local,reasons)
    # lag_scan's q window and absolute command history share timestamps; no hidden physics input.
    error=(aligned-a['q'])-bias;dynamic=selected&valid
    metrics=dict(joint_index=joint,joint_name=['index','middle','pinky','ring','thumb'][joint//4]+'_joint'+str(joint%4+1),phase=phase,source='physical_simulation' if sim else rows[0].get('source','hardware_sdk'),raw_log=str(path),raw_log_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),samples=int(selected.sum()),issued_amplitude_rad=float(np.ptp(a['u'][selected])),encoder_amplitude_rad=float(np.ptp(a['q'][selected])),static_loaded_deflection_target_minus_encoder_rad=bias,recovery_static_bias_change_rad=drift,dynamic_following_rmse_rad=float(np.sqrt(np.mean(error[dynamic]**2))),dynamic_following_p95_abs_rad=float(np.quantile(abs(error[dynamic]),.95)),lag=lag,contact_diagnostic=contact,normal_force_calibrated=False,physical_stiffness_identified=False,timing_scope='Host IPC includes scheduling+process transport+SDK call; SDK call is not an isolated USB RTT. Mechanical follow lag separately estimated at sample resolution. Legacy sim loop_ms excludes physical stepping/USB.',timing={})
    for k in ['complete_ms','compute_ms','read_ipc_ms','write_ipc_ms','read_sdk_ms','write_sdk_ms','record_ms']:
        vals=[d[k] for d,s in zip(data,selected) if s and d[k] is not None]
        metrics['timing'][k]=dict(p50=float(np.median(vals)),p95=float(np.quantile(vals,.95)),max=float(max(vals))) if vals else None
    return metrics,data,selected,aligned,error

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--reference',type=Path);p.add_argument('--joint',type=int,default=17);p.add_argument('--phase');p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert 0<=a.joint<20
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);m,rows,sel,u,error=load(a.input,a.joint,a.phase)
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    t=np.array([r['t'] for r in rows]);zero=t[sel][0];q=np.array([r['q'] for r in rows]);ut=np.array([r['ut'] for r in rows]);issued=np.array([r['u'] for r in rows]);fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
    axes[0].step(ut-zero,issued,where='post',label='Actually issued target (sim time)' if m['source']=='physical_simulation' else 'Actually issued target (ack time)');axes[0].plot(t-zero,q,'.-',ms=2,label='Encoder (read time)')
    if a.reference:
        ref,rr,rs,ru,re=load(a.reference,a.joint,a.phase);rt=np.array([r['t'] for r in rr]);rq=np.array([r['q'] for r in rr]);rz=rt[rs][0]
        axes[0].plot(rt-rz,rq,'--',label='Reference encoder, phase-aligned; not time-warped')
        axes[1].plot(rt[rs]-rz,re[rs],'--',label='Reference bias-removed error')
        comparable=m['phase']==ref['phase'] and abs(m['issued_amplitude_rad']-ref['issued_amplitude_rad'])<.0005
        m['reference_comparison']=dict(raw_log=ref['raw_log'],source=ref['source'],matched_local_excitation=comparable and m['phase']=='loaded_local_response',issued_amplitude_difference_rad=m['issued_amplitude_rad']-ref['issued_amplitude_rad'],encoder_amplitude_difference_rad=m['encoder_amplitude_rad']-ref['encoder_amplitude_rad'],static_deflection_difference_rad=m['static_loaded_deflection_target_minus_encoder_rad']-ref['static_loaded_deflection_target_minus_encoder_rad'],dynamic_rmse_difference_rad=m['dynamic_following_rmse_rad']-ref['dynamic_following_rmse_rad'],scope='Phase-aligned descriptive differences; changed contact or unmatched waveform prevents causal actuator attribution')
    axes[1].plot(t[sel]-zero,error[sel],label='Target - encoder - static baseline');axes[1].axhline(0,color='k',lw=.5)
    for key,label in [('complete_ms','Sim/legacy control preparation (no USB)' if m['source']=='physical_simulation' or rows[0]['read_ns'] is None else 'Host cycle through control flush'),('compute_ms','Compute'),('read_ipc_ms','Read host IPC'),('write_ipc_ms','Write host IPC'),('record_ms','Control record')]:
        y=np.array([np.nan if r[key] is None else r[key] for r in rows]);
        if np.isfinite(y[sel]).any():axes[2].plot(t[sel]-zero,y[sel],label=label)
    axes[0].set_title(m['source']+' | '+m['joint_name']+' | '+m['phase']);axes[0].set_ylabel('Joint angle (rad)');axes[1].set_ylabel('Dynamic error (rad)');axes[2].set_ylabel('Host cost (ms)');axes[2].set_xlabel('Seconds from selected phase');axes[2].axhline(1000/30,color='r',ls=':',label='30Hz budget; not mechanical lag');axes[2].set_xlim(-.5,t[sel][-1]-zero+.2)
    for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(a.output/'response.png',dpi=140);plt.close(fig)
    (a.output/'analysis.json').write_text(json.dumps(m,indent=2));(a.output/'aligned-timestamps.jsonl').write_text(''.join(json.dumps(dict(r,aligned_previous_issued_rad=float(v),bias_removed_error_rad=float(e)))+'\n' for r,v,e in zip(rows,u,error)))
    print(json.dumps(m));return m
if __name__=='__main__':main()
