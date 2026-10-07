"""Move the proven initial opposed pinch forward before loading or lifting.

Keeps the actual geometry/motor repairs of C560 as read-only development
priors, but alters the initial knife-relative grasp position. Only the first
lift is connected here; later manipulation must be inferred from its own
actual output, with no old functional or failed terminal state consumption.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.record_wuji_flat_table_event import record


def main():
 p=argparse.ArgumentParser();p.add_argument('--axial-shift',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 base=Path('runs/flat-table-20261006/direct/development/current-504-pickup-live-flip-candidate-v560/prefix.json');v=json.loads(base.read_text());s=v['direct_pickup'];L=np.array(s['wrist_in_knife']);L[2,3]+=a.axial_shift;s['wrist_in_knife']=L.tolist();lift=s['continuous_stages'][0];lift.update(world_translation_m=[0,0,.045],hold_acquired_hand_targets=True)
 # The old lift's measured-joint correction acts on this episode's material
 # patches and issued targets. It never imports a physical recorded state.
 s['continuous_stages']=[lift];s['loaded_middle_table_clearance_m']=.0005;s['loaded_middle_table_guard_until_s']=6.2;s['grip_motor_margin_rad']=.035;v['duration_s']=10.;v.update(candidate='D677',lineage=dict(initial_geometry='C560 tableopposedI/M+X, Thumbheel-X; axialgrasp movedbeforecontact',functional_guide='D665frontMiddle/back opposedRingcorner22mm geometry; notactualoperatorstate',axial_shift_m=a.axial_shift,lift='Owncapturedwrist45mm lift, holdownissuedhandtargets; existingmeasuredjointloadcorrection only',future='No oldRing/flip/Thumb stage connected; ownactualoutput controlsnext'),scope=__doc__)
 v['goal8_status']='D677 forwardinitialpinch candidate; no completeGoal or inheritanceofC560stablecap';(a.output/'prefix.json').write_text(json.dumps(v,indent=2));print(json.dumps(v['lineage']))
 e=record('forward_initial_opposed_pinch_prepared',[str(a.output/'prefix.json')],config=dict(candidate='D677',grasp_end='Pendingownfreshnativepickup',support_layout='Forward20mm I/M+X andThumbheel-X establishedbeforelift; Ringinitialidle, no twofinger restriction',control='Original503motorloading/earlyThumbclearance; livepredictiveMiddlefloor0.5mm; ownacquiredliftandloadcorrection, no oldactualstate',uncertainty='676 nonThumbtablepinch stillfails lift; canproven opposedThumbinitialpinch movedforwardestablish neededanteriorMiddle region beforeload instead of failedinhandforwardtranslation?',decision='Actualsafeforwardpickup -> ownactualRing/flip planning keeping axialregion, then currentThumbpathcapacity. Earliestactualfailure -> itsgeometry/trajectory, no frozenoldfront'),next_step='Freshdirectforwardpinch10s only; newfrontmeansnewactualhandoff beforeanybackstage')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')

if __name__=='__main__':main()
