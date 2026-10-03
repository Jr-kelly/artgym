"""Reuse completed public-estimate brace recipes; add sequential motor paths."""
import copy,json,pathlib,time
from concurrent.futures import ThreadPoolExecutor
from scripts.plan_wuji_braced_support import staged_transfer
from scripts.record_wuji_support_goal import record

R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/support-pressure-20261003'
B=R/'runs/support-pressure-20261003/staged-support-training-config-v88';B.mkdir(parents=True,exist_ok=False)
source=R/'runs/support-pressure-20261003/braced-support-training-config-v83'
scene=json.loads((D/'braced-support-estimate-scene256-v83.json').read_text())
original_scene=json.loads((D/'joint-looser-estimate-scene256-v32.json').read_text())
record('staged_support_family_v88_started',evidence=str(B.relative_to(R)),config={'observations':256,'reuse':'completedv83publicrecipes','rerun_static_wrench':False},next='Preserve everyobservation/physicalslot, label estimatedpathfailures')
begin=time.monotonic()

def one(item):
    i,row=item;row=copy.deepcopy(row);folder=B/('%04d'%i);folder.mkdir()
    failed=bool(row['audit'].get('brace_fallback'))
    if not failed:
        assert original_scene['initial_estimated_plans'][i]['estimate']==row['estimate']
        original_target=dict(post_lift_target_q=original_scene['initial_estimated_plans'][i]['support_target_q'])
        brace=dict(post_lift_target_q=row['support_target_q'])
        try:
            support=staged_transfer(row['motor_plan'],original_target,brace)
            row['support_motor_waypoints']=support['motor_waypoints']
            row['audit']['staged_transfer']=support['staged_transfer_audit']
        except (AssertionError,ValueError) as error:
            failed=True;row['audit']['staged_transfer_failure']=str(error)
    row['audit']['staged_transfer_fallback']=failed
    row['audit']['staged_transfer_fallback_scope']='Shared publicestimate planning check; original public-estimate recipe retained, no physicalstate/assetID selection or filtering'
    (folder/'planned-row.json').write_text(json.dumps(row,indent=2));return i,row

with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,enumerate(scene['initial_estimated_plans'])))
rows.sort();scene['initial_estimated_plans']=[row for _,row in rows]
scene['staged_support_scope']='Sequential index/middle withdraw/cross/recontact from publicestimate only; all64 physicalslots and256observations retained with labelled sharedfallbacks. Finish14.2s, actualhistory50before16s.'
out=D/'staged-support-estimate-scene256-v88.json';out.write_text(json.dumps(scene,separators=(',',':')))
result=dict(observations=256,physical_slots=64,staged_paths=sum(bool(row.get('support_motor_waypoints')) for _,row in rows),fallbacks=sum(row['audit']['staged_transfer_fallback'] for _,row in rows),seconds=time.monotonic()-begin,scope='Public-estimate motorplanning only, not collision/force/physical certification; no initialstate filtering')
(D/'staged-support-family-preparation-v88-results.json').write_text(json.dumps(result,indent=2));record('staged_support_family_v88_closed',evidence=str(out.relative_to(R)),config=result,next='Short matched ordinary/absorbing/frozen-thumb adaptation; keep originalcontroller bounds and allphysicalattempts');print(json.dumps(result))
