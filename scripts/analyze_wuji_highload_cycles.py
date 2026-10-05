"""Evaluation-only transient rotation, all recorded cycles and known-load work.

Original functional criterion is calculated separately without modification.
This report never upgrades a criterion failure or equates axial test load to B.
"""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

def analyze(path):
    z=np.load(path/'trace.npz');t=z['time'];report=json.loads((path/'report.json').read_text())
    asset=Path(report['physical_asset']);root=Path(__file__).resolve().parents[1]
    if not asset.is_absolute():asset=root/asset
    if not asset.exists():
        for prefix in ['runs/traction-20261005/','runs/highload-20261005/']:
            if prefix in str(asset):asset=root/(prefix+str(asset).split(prefix,1)[1]);break
    limit=ET.parse(asset).find('.//joint[@type="prismatic"]/limit');lower=float(limit.get('lower'));upper=float(limit.get('upper'))
    wr=Rotation.from_quat(z['wrist'][:,3:7]);ob=Rotation.from_quat(z['object'][:,3:7]);relative=wr.inv()*ob;anchor=np.flatnonzero(t>=16)[0]-1
    delta=relative[anchor].inv()*relative;rv=delta.as_rotvec();angle=delta.magnitude()
    axis=delta.apply(np.tile([0.,0.,1.],(len(t),1)));axis_tilt=np.arccos(axis[:,2].clip(-1,1))
    contact=z['pair_slider_contact_substep_fraction'][:,0]
    rows=[]
    for cycle in range(int((t[-1]-16+.1)//10)):
        start=16+cycle*10;ids=np.flatnonzero((t>=start)&(t<start+10));peak=ids[np.argmax(angle[ids])]
        stages=[]
        for a,b in [(start,start+5),(start+5,start+10)]:
            ix=np.flatnonzero((t>=a)&(t<=b));tail=np.flatnonzero((t>b-1)&(t<=b+.001))
            stages.append(dict(window_s=[a,b],median_endpoint_mm=float((np.median(z['slider'][tail])-lower)*1000),actual_signed_travel_mm=float((z['slider'][ix[-1]]-z['slider'][ix[0]])*1000),peak_angle_rad=float(angle[ix].max()),thumb_contact_fraction=float(contact[ix].mean()),minimum_slider_distance_from_either_stop_mm=float(np.minimum(z['slider'][ix]-lower,upper-z['slider'][ix]).min()*1000)))
        rows.append(dict(cycle=cycle+1,peak_time_s=float(t[peak]),peak_rotation_rad=float(angle[peak]),peak_rotvec=rv[peak].tolist(),time_above_original_envelope_s=float((angle[ids]>.6).sum()/30),axis_tilt_at_peak_rad=float(axis_tilt[peak]),maximum_axis_tilt_rad=float(axis_tilt[ids].max()),thumb_contact_at_peak=float(contact[peak]),body_contact_fraction_at_peak=z['pair_body_contact_substep_fraction'][peak].tolist(),normal_moments_at_peak=z['pair_all_contact_normal_moment_knife_mean_Nm'][peak].tolist(),return_rotation_rad=float(angle[ids[-1]]),stages=stages))
    result=dict(trial=str(path),cycles=rows,scope=__doc__,B_original_axial_N=None,C_original_rail_N=None)
    loadfile=path/'opposing-load-physical-steps.jsonl'
    if not loadfile.exists():
        candidates=list(path.glob('*test*jsonl'));loadfile=candidates[0] if candidates else loadfile
    if loadfile.exists():
        values=[json.loads(s) for s in loadfile.read_text().splitlines()];values=[r for r in values if r['time_s']>16]
        result['known_test_load']=dict(samples=len(values),active_fraction=float(np.mean([r['active'] for r in values])),applied_abs_N=sorted(set(abs(r['applied_axial_test_force_N']) for r in values)),work_J=float(sum(r['work_J'] for r in values)),positive_wrong_direction_work_J=float(sum(max(0,r['work_J']) for r in values)),scope='Balanced opposing test load, not measured total axial traction; positive work occurs only in wrong-direction motion. Does not certify complete task unless all original checks pass.')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--trials',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[analyze(p) for p in a.trials];a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
