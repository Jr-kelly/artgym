"""Summarize an explicitly declared, frozen-policy reset-range stress experiment."""
import argparse,datetime,hashlib,json
from pathlib import Path
import numpy as np
from scripts.summarize_wuji_rgb_independent import rate

def main():
 p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--cohort',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 audit=json.loads(a.audit.read_text());m=json.loads((a.cohort/'manifest.json').read_text());assert audit['status']=='verified_complete' and audit['physics_transitions']==398400 and len(audit['audits'])==8
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(a.cohort/'mixed332.npy')==m['initial_states_sha256']==audit['initial_states_sha256'];assert audit['evaluation_seed']==m['seed'];assert m['no_outcome_filter'] and m['physics_transitions']==0 and m['one_x_recipe_bitwise_verified'];assert m['created']>m['models_frozen']
 assert sha(a.cohort/'mixed.pth')==m['candidate']['sha256']==audit['artifacts']['mixed']['sha256'];conditions={};vectors=[]
 for sec in [2,5]:
  c=audit['conditions'][f'mixed-{sec}s'];records=c['records'];assert set(map(int,records))==set(range(332));values=np.array([records[str(i)]['stable_full_all_endpoints'] for i in range(332)],dtype=bool);vectors.append(values[:300]);groups=[rate(values[i:i+100]) for i in [0,100,200]];total=rate(values[:300]);passed=total['rate']>=.95 and all(x['rate']>=.90 for x in groups)
  conditions[str(sec)]=dict(new300=total,trained_grasp_groups=groups,reused_fourth32=rate(values[300:]),body_only=rate([records[str(i)]['body_only'] for i in range(300)]),endpoints=rate([records[str(i)]['all_endpoints_held'] for i in range(300)]),working_threshold_passed=passed)
 result=dict(status='complete',finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),conditions=conditions,passed_both_clocks=all(x['working_threshold_passed'] for x in conditions.values()),both_clocks_same_state=rate(vectors[0]&vectors[1]),scope=m['scope'],perturbations=m['perturbations'],audit_sha256=sha(a.audit),manifest_sha256=sha(a.cohort/'manifest.json'),source_sha256=sha(Path(__file__)))
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
