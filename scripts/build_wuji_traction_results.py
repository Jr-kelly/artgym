"""Combine original criterion results and signed physical travel; no inferred forces."""
import json
from pathlib import Path
from scripts.analyze_wuji_traction import analyze
R=Path(__file__).resolve().parents[1];B=Path('runs/traction-20261005');D=R/'research/traction-20261005'
def main():
    paths=[]
    old=Path('runs/wrap-force-20261004')
    for label,path in [('Baseline .20',old/'continuous/index-wrap-v8-direct-corner-mass-corrected-v4'),('Baseline .35',old/'validation/wrap-frozen-v12-load035-v1'),('Baseline .50',old/'validation/wrap-frozen-v12-load050-v1')]:paths.append((label,path,'baseline development'))
    paths += [('V13 .35 local video',B/'selected-full-video-v13/simulation','frozen repeat'),
              ('V13 .35 remote',B/'continuous/cartesian-recenter-load0.35-v12','development selected'),
              ('V13 .50 remote',B/'continuous/cartesian-recenter-load0.50-v12','development boundary'),
              ('V13 .20 remote',B/'validation/selected-nominal020-v13/simulation','frozen nominal regression'),
              ('V13 .50 local video',B/'validation/selected-highload050-video-v16/simulation','frozen boundary'),
              ('V13 thin .35',B/'validation/selected-thin035-v13/simulation','development geometry regression'),
              ('V10 .35 local borderline failure',B/'selected-full-video-v10/simulation','earlier candidate rejected for return margin'),
              ('Restored V13 .35',B/'validation/restored-v17/simulation','independent empty-directory restore')]
    for label in ['thin130x14x10','nominal-axial-plus5mm','012','015']:paths.append(('V13 '+label+' .20',B/('validation/regression-'+label+'-020-v18/simulation'),'development geometry regression'))
    for label in ['fresh01-v15','fresh02-v15','fresh03-v15','fresh04-v15r1']:paths.append((label,B/('validation/'+label+'/simulation'),'fresh joint validation, never tuned'))
    for label in ['thumbzero-original-load0.35-v9','thumbzero-tangent-recenter-load0.35-v9','cartesian-tracking10-load0.50-v12','support0.00-tracking1-load0.50-v14','support0.04-tracking1-load0.50-v14']:paths.append((label,B/('continuous/'+label),'development ablation, unselected'))
    rows=[];missing=[]
    for label,path,scope in paths:
        f=R/path/'functional-evaluation.json'
        if not f.exists():missing.append(dict(label=label,trial=str(path)));continue
        row=dict(label=label,trial=str(path),scope=scope,evaluation=json.loads(f.read_text()))
        row['physical_stages']=analyze(R/path)['windows']
        row['normal_A_mean_N']=sum(w['thumb_normal_mean_N'] for w in row['physical_stages'])/4
        row['axial_B_N']=None;row['rail_C_N']=None
        rows.append(row)
    result=dict(selected='FROZEN-CANDIDATE-V13.json',actor_sha256='ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a',new_training=False,
       implementation='Original default grasp and S120 support; thumb residual disabled; at task reversal, measured joint deflection mapped through initial-geometry axial FK Jacobian reanchors the full 40 mm reference with fixed bounds. No current object/contact/load input.',
       conclusion='Reversal/reference and learned thumb mismatch contribute to cycle decay. V13 improves .35 full continuous behavior across local/remote. .50 tracking recovers endpoints but exceeds relative rotation envelope, leaving support coordination unresolved. Torque saturation and sole force insufficiency are not established.',
       force_scope=dict(A='Original calibrated thumb-slider normal, 240 Hz pairs aggregated to 30 Hz.',B='Unmeasured on original knife; null, not zero.',C='Unmeasured actual rail reaction; null, not zero.',D='Whole-task simulation capacity profile at .35, with location/time dependent caps; not .35 N measured resistance, added-load capacity, real force, or maximum capability.'),
       delivery_complete=False,functional_demo_ready=True,necessary_generalization_resolved=False,axial_force_measurement_resolved=False,hardware_ready=False,real_robot_ran=False,goal_complete=False,trials=rows,missing=missing)
    result['resources']={}
    for label in ['local','development']:
        f=R/B/'resources'/label/'status.json'
        if f.exists():result['resources'][label]=json.loads(f.read_text())
    result['resource_scope']='Observed windows only; four-hour coverage is incomplete and remote mean is below 26%. No filler work; resource compliance is not claimed.'
    (D/'DELIVERY-RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(dict(trials=len(rows),missing=missing)))
if __name__=='__main__':main()
