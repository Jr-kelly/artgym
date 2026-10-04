import json,numpy as np
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
b=Path('runs/antirotation-grasp-20261004');result={}
for name in ['opposed-table-strong-2cycles-v4','actual-table-index-corner-2cycles-v5']:
 trial=b/'continuous'/name;t=np.load(trial/'trace.npz');times=t['time'];forces=t['pair_force_normal_contribution_world_mean_N'];phases={}
 for label,mask in [('before',(times>=12)&(times<12.2)),('settled',(times>=15)&(times<16)),('operate',times>=16)]:
  phases[label]={'index_body_contact_substep_fraction':float(t['pair_body_contact_substep_fraction'][mask,1].mean()),'index_body_mean_normal_contribution_norm_N':float(np.linalg.norm(forces[mask,1,0],axis=-1).mean()),'index_body_frame_mean_normal_contribution_norm_max_N':float(np.linalg.norm(forces[mask,1,0],axis=-1).max()),'thumb_slider_normal_mean_N':float(t['pair_slider_pressure_mean_N'][mask,0].mean())}
 result[name]=phases
out=b/'continuous/actual-index-contact-mechanism-v1.json';out.write_text(json.dumps(result,indent=2));print(json.dumps(result));record('actual_index_contact_mechanism_compared',evidence=str(out),conclusion='Full1080frames exactbodycontactsubstep fractions and frame-meannormalvectornorm only, no friction wrench. Prior rawsubstep dump containsrepresentativeblocks, lacks15–16s; originaldiagnosticfailed, correctedfulltrace. Continuousendpointsstillfail, bodyrelative rotationworse; no unchangedcornerpressureextension.',next='Choose pure sidecontact ifcornerrealpressure adds destabilizing underside load; awaitfiniteadaptationfreeze')
