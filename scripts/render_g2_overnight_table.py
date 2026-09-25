"""Compact stage-aware CSV from the detailed immutable-trace audit."""
import argparse,csv,json
from pathlib import Path


def mm(value):return None if value is None else value*1000


def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous summary table')
    data=json.loads(a.summary.read_text());rows=[]
    for trial in data['trials']:
        cmd=trial.get('command',[]);group=cmd[cmd.index('--group')+1] if '--group' in cmd else trial.get('group')
        score=trial.get('score',{});stages=trial.get('gait_stages',[]);end=stages[-1] if stages else {}
        good=[s for s in stages if s['stage_completed']];steps=trial.get('operation_steps',0) or 0
        failure=trial.get('abort',{});first=trial.get('first_instability_time_s')
        op_first=trial.get('operation_first_instability')
        if op_first is not None:first=min(first,op_first['time_s']) if first is not None else op_first['time_s']
        row=dict(trial=trial['name'],kind='development',group=group,status=trial['status'],physical_execution=trial.get('physical_execution'),
            actual_tabletop_route=group in ['B','C'] and trial.get('physical_execution',False),
            lift_success=score.get('lift_success') if group!='A' else None,
            flip_success=trial.get('flip',{}).get('retained') if trial.get('flip') else None,
            last_scored_gait=end.get('name'),last_scored_gait_pass=end.get('stage_completed'),
            last_passed_gait=good[-1]['name'] if good else None,
            g1_achieved_at_some_stage=trial.get('g1_passed'),
            final_gait_world_translation_mm=1000*end['world_position_max_m'] if end else None,
            final_gait_world_rotation_rad=end.get('world_rotation_max_rad'),
            final_gait_contacts_thumb_index_middle_ring_pinky=json.dumps(end.get('contact_fraction_thumb_index_middle_ring_pinky')) if end else None,
            first_world_instability_s=first,first_low_after_lift_s=trial.get('first_low_object_after_commanded_lift',{}).get('time_s'),
            entered_policy=steps>0,operation_steps=steps,
            basic_10mm=score.get('basic_10mm') if steps else None,strict_2mm=score.get('strict_2mm') if steps else None,
            operation_fixed_world_stable=score.get('stable_world_10mm_025rad') if steps else None,
            slider_travel_mm=mm(score.get('slider_travel_m')) if steps else None,
            endpoint_max_errors_mm=json.dumps([mm(v['max_error_m']) for v in score['endpoints']]) if steps and 'endpoints' in score else None,
            operation_drop=score.get('physical_drop_detected') if steps else None,
            operation_world_drift_mm=mm(score.get('world_drift_max_m')) if steps else None,
            operation_world_rotation_rad=score.get('world_rotation_max_rad') if steps else None,
            operation_hand_drift_mm=mm(score.get('hand_relative_drift_max_m')) if steps else None,
            operation_hand_rotation_rad=score.get('hand_relative_rotation_max_rad') if steps else None,
            required_operation_success=score.get('whole_stable_success') if steps else None,
            continuous_whole_success=bool(group in ['B','C'] and steps and score.get('whole_stable_success',False)),
            abort_phase=failure.get('last_phase'),abort_reason=failure.get('message',failure.get('error',failure.get('exception'))),
            raw_failure_class=trial.get('failure_class'),
            caution=('Independent preset A; no acquisition' if group=='A' else 'No policy evaluation; not a teacher/student failure' if not steps else 'Development run; not independent validation'))
        rows.append(row)
    with a.output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(output=str(a.output),rows=len(rows),policy_evaluations=sum(r['entered_policy'] for r in rows),continuous_successes=sum(r['continuous_whole_success'] for r in rows))))


if __name__=='__main__':main()
