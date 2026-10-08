"""Create local, evidence-linked device and position-response profiles; no calibration invented."""
import argparse,json,hashlib,datetime,csv
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['device-template','reference-template','import-device','confirm-device','confirm-response']);p.add_argument('--bundle',type=Path,default=Path('research/rear-sim2real-20261009/bundle-deploy-v8.json'));p.add_argument('--output',type=Path,required=True);p.add_argument('--device-profile',type=Path);p.add_argument('--evidence',type=Path,nargs='+');p.add_argument('--operator-confirmed',action='store_true');p.add_argument('--normal-force-calibrated',action='store_true');p.add_argument('--reference-csv',type=Path);p.add_argument('--zero-evidence',type=Path);p.add_argument('--zero-source',choices=['factory_calibration','manufacturer_definition','observed_reference_pose']);p.add_argument('--device-read',type=Path);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    s=json.loads(a.bundle.read_text());utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if a.mode=='reference-template':
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['joint_name','model_from_device_sign','device_zero_rad','known_model_reference_rad','measured_device_reference_rad','zero_verified']);w.writeheader()
            for n in s['runtime_joint_names']:w.writerow(dict(joint_name=n,model_from_device_sign=1,device_zero_rad=0,known_model_reference_rad='',measured_device_reference_rad='',zero_verified='false'))
        print(a.output);return
    if a.mode=='device-template':
        value=dict(format='wuji-device-calibration-v1',runtime_joint_names=s['runtime_joint_names'],model_from_device_sign=[1]*20,device_zero_rad=[0.]*20,axes_verified=False,absolute_zero_verified=False,axes_zeros_limits_verified=False,source='provisional identity by name; physical axes/zeros NOT verified',notes='Small checks verify axes only. Use import-device with a named reference CSV and independent trusted zero evidence; do not hit endpoints.',created_utc=utc)
    elif a.mode=='import-device':
        if not (a.reference_csv and a.zero_evidence and a.zero_source and a.device_read and a.operator_confirmed):raise ValueError('Need named reference CSV, trusted zero evidence/source, real read folder and operator observation')
        rows=list(csv.DictReader(a.reference_csv.open()));by={r['joint_name']:r for r in rows}
        if len(rows)!=20 or set(by)!=set(s['runtime_joint_names']):raise ValueError('Reference must contain exactly twenty unique model joint names')
        if any(r['zero_verified'].lower()!='true' for r in rows):raise ValueError('Provisional zeros are not trusted calibration; verify reference evidence first')
        sign=[float(by[n]['model_from_device_sign']) for n in s['runtime_joint_names']]
        # An observed reference can be entered in two named columns; no manual offset algebra.
        zero=[]
        for n,g in zip(s['runtime_joint_names'],sign):
            r=by[n]
            if r.get('known_model_reference_rad','') and r.get('measured_device_reference_rad',''):zero.append(float(r['measured_device_reference_rad'])-g*float(r['known_model_reference_rad']))
            else:zero.append(float(r['device_zero_rad']))
        if not np.all(np.isin(sign,[-1.,1.])) or not np.isfinite(zero).all():raise ValueError('Signs must be +/-1 and offsets finite radians')
        meta=json.loads((a.device_read/'metadata.json').read_text())
        if meta.get('source')!='hardware_sdk' or not meta.get('device_identity_sha256'):raise ValueError('Reference import needs identified real-hand read, not fixture')
        value=dict(format='wuji-device-calibration-v1',runtime_joint_names=s['runtime_joint_names'],model_from_device_sign=sign,device_zero_rad=zero,axes_verified=False,absolute_zero_verified=True,absolute_zero_source=a.zero_source,absolute_zero_evidence_sha256=sha(a.zero_evidence),reference_csv_sha256=sha(a.reference_csv),reference_model_urdf_sha256=sha(s['hand_model_urdf']),device_identity_sha256=meta['device_identity_sha256'],device_lower_rad=meta['metadata']['lower_rad']['values'],device_upper_rad=meta['metadata']['upper_rad']['values'],axes_zeros_limits_verified=False,source='Operator imported independent named zero reference; axis checks still required',created_utc=utc)
        readings=[json.loads(l) for l in (a.device_read/'control.jsonl').read_text().splitlines()]
        ticks=[r['device_telemetry']['device_system_time_raw'] for r in readings]
        windows=[r['host_read_sample_ns'] for r in readings]
        value.update(system_clock_advances_at_30hz_observed=len(ticks)>=30 and all(a!=b for a,b in zip(ticks,ticks[1:])) and all(20000000<=b-a<=66666667 for a,b in zip(windows,windows[1:])),system_clock_evidence_sha256=sha(a.device_read/'control.jsonl'),system_clock_scope='Observed opaque counter advance at 30Hz; no raw tick unit or pure USB lag inferred')
    else:
        if not a.operator_confirmed or not a.evidence:raise ValueError('Actual local evidence and operator observations required; elapsed time is not confirmation')
        data=[json.loads((r/'summary.json').read_text()) for r in a.evidence];fixture=any(r['source']=='sdk_fixture_no_device' for r in data)
        if a.mode=='confirm-device':
            if a.device_profile is None:raise ValueError('Edited provisional device profile required')
            value=json.loads(a.device_profile.read_text())
            if fixture:raise ValueError('Fixture cannot verify hardware axes/zeros')
            if not value.get('absolute_zero_verified') or not value.get('absolute_zero_evidence_sha256'):raise ValueError('Twenty small motions cannot establish absolute zero; import-device with independent zero evidence first')
            touched=set()
            for folder in a.evidence:
                meta=json.loads((folder/'metadata.json').read_text())
                if meta.get('calibration_sha256')!=sha(a.device_profile):raise ValueError('Axis checks must use this imported mapping; rerun only checks invalidated by a mapping correction')
                rows=[json.loads(l) for l in (folder/'control.jsonl').read_text().splitlines()]
                if not rows:continue
                measured=np.array([r['encoder_model_rad'] for r in rows]);responded=set(np.flatnonzero(np.ptp(measured,axis=0)>.0005).tolist())
                base=np.asarray(rows[0]['encoder_model_rad'])
                for row in rows:
                    if row['issued_target_rad'] is not None:touched.update(set(np.flatnonzero(abs(np.asarray(row['issued_target_rad'])-base)>.002).tolist()) & responded)
            if len(touched)!=20:raise ValueError('Need small-action observations for all twenty joints before confirming model axes/zeros')
            identities={json.loads((folder/'metadata.json').read_text())['device_identity_sha256'] for folder in a.evidence}
            if len(identities)!=1 or None in identities:raise ValueError('Checks must use one identified real hand')
            if next(iter(identities))!=value.get('device_identity_sha256'):raise ValueError('Zero evidence and axis checks belong to different hands')
            value.update(device_identity_sha256=next(iter(identities)),axes_verified=True,axes_zeros_limits_verified=True,source='hardware_named_axes_checks_plus_independent_absolute_zero_reference',evidence=[str(x) for x in a.evidence],verified_utc=utc)
        else:
            if any(r['mode']!='response' for r in data):raise ValueError('Use actual loaded response logs')
            if any(r['loop_ms']['max'] is None or r['loop_ms']['max']>1000/30 for r in data):raise ValueError('Complete read/write/ack/log cycle exceeded 33.33ms')
            ranges=[];analyses=[]
            for folder in a.evidence:
                rows=[json.loads(l) for l in (folder/'control.jsonl').read_text().splitlines() if json.loads(l)['phase']=='loaded_local_response']
                if len(rows)<30:raise ValueError('At least one second of local loaded response required')
                q=np.array([r['encoder_model_rad'] for r in rows]);u=np.array([r['issued_target_rad'] for r in rows]);span=np.ptp(u,axis=0);j=int(span.argmax());measured=float(np.ptp(q[:,j]))
                if span[j]<.003 or measured<.0005:raise ValueError('No measurable local response; inspect direction, preload and firmware')
                if max(r['loop_ms'] for r in rows)>1000/30:raise ValueError('Loaded 30Hz response timing failed')
                from scripts.analyze_wuji_rear_response import load
                analysis,_,_,_,_=load(folder,j);analyses.append(analysis)
                ranges.append(dict(joint=s['runtime_joint_names'][j],issued_range_rad=float(span[j]),encoder_range_rad=measured,scope='Local position response; no stiffness/force identification'))
            if not fixture and a.device_profile is None:raise ValueError('Verified device profile required')
            value=dict(format='wuji-local-response-v2',bundle_sha256=sha(a.bundle),device_calibration_sha256=sha(a.device_profile) if a.device_profile else None,source='sdk_fixture_no_device' if fixture else 'hardware_local_response',position_response_recorded=True,bounded_probe_permitted=True,full_action_reliability='not_established',response_analysis=analyses,pressure_compensation_enabled=True,normal_force_calibrated=a.normal_force_calibrated and not fixture,nominal_pressure_stiffness_status='Original effective simulated model remains a working hypothesis; local functional response checked, not identified physical stiffness',local_response=ranges,evidence=[str(x) for x in a.evidence],operator_confirmed=True,verified_utc=utc)
            if a.normal_force_calibrated:raise ValueError('Separate aligned force evidence import is not implemented; cannot mark force calibrated from position logs')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2));print(str(a.output))
if __name__=='__main__':main()
