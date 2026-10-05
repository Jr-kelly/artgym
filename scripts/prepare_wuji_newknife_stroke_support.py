"""Known-command support normal-moment schedule from initial geometry only.
Uses the same inverse-static model as initial preload. Not a force measurement.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--actuator-spec',type=Path,required=True);a=p.parse_args();assert not a.output.exists();shutil.copytree(a.base,a.output)
 (a.output/'actual-transfer-stroke-audit.json').rename(a.output/'original-static-stroke-audit.json')
 ref=json.loads((a.output/'reference.json').read_text());plan=json.loads((a.output/'motor-plan.json').read_text());spec=plan['support_inverse_static_preload'];act=json.loads(a.actuator_spec.read_text());kp=np.array(act['kp'])[act['hand_indices']];rows=spec['rows'];points=np.array([r['contact_m'] for r in rows]);matrix=np.array([np.ones(3),points[:,0],points[:,2]]);thumb_N=spec['thumb_normal_proxy_N'];z0=-.02205+plan['initial_geometry_estimate']['slider_contact_shift_m'][2];forces0=np.array([r['requested_normal_proxy_N'] for r in rows]);audit=[]
 for r in ref['rows']:
  force=np.linalg.solve(matrix,[thumb_N+spec['normal_weight_N'],0,thumb_N*(z0+r['shift_m'])]);assert np.all(force>0);offset=np.zeros(16)
  for support,n,n0 in zip(rows,force,forces0):
   ids=support['ids'];jac=np.array(support['jacobian_m_rad']);offset[ids]=jac.T@np.array([0,n-n0,0])/kp[ids]
  r['support_offset_rad']=offset.tolist();audit.append(dict(shift_m=r['shift_m'],requested_normal_proxy_N=force.tolist(),support_offset_rad=offset.tolist()))
 ref.update(support_reference_anchor=True,stroke_support_scope=__doc__);(a.output/'reference.json').write_text(json.dumps(ref,indent=2));(a.output/'stroke-support-model.json').write_text(json.dumps(dict(scope=__doc__,rows=audit),indent=2));print(json.dumps(dict(min_proxy_N=min(min(r['requested_normal_proxy_N']) for r in audit),max_proxy_N=max(max(r['requested_normal_proxy_N']) for r in audit),maximum_support_offset_rad=max(max(abs(x) for x in r['support_offset_rad']) for r in audit))))
if __name__=='__main__':main()
