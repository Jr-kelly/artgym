"""Select longest certified estimate-only prefix; never relax clearance criteria.
This checks transferred motor anchors. Runtime correction still needs physical check.
"""
import argparse,json,shutil,subprocess,sys,numpy as np
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--min-stroke',type=float,default=.030);a=p.parse_args();assert not a.output.exists();shutil.copytree(a.base,a.output)
op=a.output/'operation';ref0=json.loads((op/'reference.json').read_text());history=[]
for length in np.arange(ref0['command_travel_m'],a.min_stroke-.0001,-.001):
 ref=json.loads(json.dumps(ref0));rows=[r for r in ref0['rows'] if r['shift_m']<length-1e-9];endpoint={}
 for k,v in ref0['rows'][0].items():
  if isinstance(v,bool): endpoint[k]=all(r[k] for r in ref0['rows'])
  elif isinstance(v,(int,float,list)):
   vals=np.array([r[k] for r in ref0['rows']]);xs=[r['shift_m'] for r in ref0['rows']]
   endpoint[k]=float(np.interp(length,xs,vals)) if vals.ndim==1 else [float(np.interp(length,xs,vals[:,j])) for j in range(vals.shape[1])]
  else:endpoint[k]=v
 endpoint['shift_m']=float(length);ref['rows']=rows+[endpoint];ref['command_travel_m']=float(length);(op/'reference.json').write_text(json.dumps(ref,indent=2))
 audit=a.output/('prefix-%0.0fmm-audit.json'%(length*1000));cmd=[sys.executable,'-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(op/'reference.json'),'--motor-plan',str(op/'actual-transfer-motor-plan.json'),'--knife-spec',str(op/'estimated-collision/spec.json'),'--samples','81','--output',str(audit)]
 with audit.with_suffix('.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 evidence=json.loads(audit.read_text());history.append(dict(length_m=float(length),passed=evidence['all_passed'],rate_limit_required=evidence['rate_limit_required'],audit=str(audit)))
 if evidence['all_passed'] and not evidence['rate_limit_required']:
  shutil.copyfile(audit,op/'actual-transfer-stroke-audit.json');result=dict(passed=True,stroke_m=float(length),prepared=str(a.output/'pickup'),operation_prepared=str(op),selection_history=history,scope=__doc__);(a.output/'prefix-selection.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));break
else:
 (a.output/'prefix-selection.json').write_text(json.dumps(dict(passed=False,selection_history=history),indent=2));raise RuntimeError('No prefix with required task reserve')
