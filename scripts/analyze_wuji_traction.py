"""Align original-contact diagnostics; no unavailable axial forces are inferred."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

def analyze(trial):
    z=np.load(trial/'trace.npz');t=z['time']
    physics=json.loads((trial/'physics.json').read_text())
    report=json.loads((trial/'report.json').read_text())
    import xml.etree.ElementTree as ET
    asset=Path(report['physical_asset'])
    if not asset.is_absolute():asset=Path(__file__).resolve().parents[1]/asset
    if not asset.exists() and '/runs/traction-20261005/' in str(asset):
        asset=Path(__file__).resolve().parents[1]/('runs/traction-20261005/'+str(asset).split('/runs/traction-20261005/',1)[1])
    lower=float(ET.parse(asset).find('.//joint[@type="prismatic"]/limit').get('lower'))
    hand=np.asarray(physics['hand_indices']);thumb=hand[16:]
    ob=Rotation.from_quat(z['object'][:,3:7]);wr=Rotation.from_quat(z['wrist'][:,3:7])
    rel=wr.inv()*ob;origin=np.flatnonzero(t>=16)[0]-1
    rot=(rel[origin].inv()*rel).as_rotvec()
    pad=ob.inv().apply(z['pad_poses'][:,0,:3]-z['object'][:,:3])
    offset=pad[:,2]-z['slider']
    fraction=abs(z['torque'][:,thumb])/np.asarray(physics['effort'])[thumb]
    rows=[]
    for start,end in [(16,21),(21,26),(26,31),(31,36)]:
        ids=np.flatnonzero((t>=start)&(t<=end));last=np.flatnonzero((t>end-1)&(t<=end))
        a,b=ids[0],ids[-1]
        rows.append(dict(window_s=[start,end],start_slider_from_lower_mm=float((z['slider'][a]-lower)*1000),
            final_slider_from_lower_mm=float((z['slider'][b]-lower)*1000),
            actual_signed_travel_mm=float((z['slider'][b]-z['slider'][a])*1000),
            median_endpoint_mm=float((np.median(z['slider'][last])-lower)*1000),
            thumb_pad_center_minus_slider_axis_mm=[float(offset[a]*1000),float(offset[b]*1000)],
            relative_rotation_start_end_rad=[rot[a].tolist(),rot[b].tolist()],
            thumb_contact_fraction=float(z['pair_slider_contact_substep_fraction'][ids,0].mean()),
            thumb_normal_mean_N=float(z['pair_slider_pressure_mean_N'][ids,0].mean()),
            body_contact_fraction_by_finger=z['pair_body_contact_substep_fraction'][ids].mean(0).tolist(),
            recorded_thumb_effort_fraction_max=float(fraction[ids].max())))
    return dict(trial=str(trial),windows=rows,scope='Evaluation only. Pad center offset is a kinematic migration proxy, not the contact centroid. Effort is the commanded simulator torque, sampled30Hz; substep peaks may be missed. Normal force A is calibrated pair normal. Original total axial B and actual rail reaction C remain unavailable; brake capacity is configuration only.',weight_sha256=report['weight_sha256'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--trials',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=[analyze(x) for x in a.trials];a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2))
    for row in result:print(row['trial'],[(w['window_s'],round(w['median_endpoint_mm'],2),round(w['actual_signed_travel_mm'],2),round(w['thumb_contact_fraction'],3)) for w in row['windows']])
if __name__=='__main__':main()
