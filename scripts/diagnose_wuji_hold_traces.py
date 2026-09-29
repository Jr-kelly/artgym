"""Analyze existing frozen expert traces without new simulation or policy selection."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records, summaries = [], []
    for source in (3, 11):
        for seconds in (2, 5):
            directory = args.previous_root/'runs/multigrasp-20260928'/f'expert_row{source}_seed2810-fixed{seconds}'/'evidence'
            with np.load(directory/'trace.npz') as archive:
                trace = {key: archive[key] for key in archive.files}
            report = json.loads((directory/'report.json').read_text())
            steps = seconds * 30
            valid = trace['active'] & ~trace['fall'] & ~trace['invalid']
            error = trace['slider']-trace['goal']
            for env in range(32):
                for start in range(0, 600, steps):
                    end = start+steps
                    within = (np.abs(error[start:end, env]) < .002) & valid[start:end, env]
                    streak = 0
                    first = None
                    longest = 0
                    for offset, hit in enumerate(within):
                        streak = streak+1 if hit else 0
                        longest = max(longest, streak)
                        if streak >= 9 and first is None:
                            first = offset
                    reexit = bool(first is not None and (~within[first+1:]).any())
                    final = slice(end-9, end)
                    records.append(dict(source=source, protocol=f'fixed{seconds}', trial=env,
                        stage=start//steps, goal_m=float(trace['goal'][start, env]),
                        attained_300ms=first is not None, final_300ms=bool(within[-9:].all()),
                        left_after_attainment=reexit, first_attainment_s=(first+1)/30 if first is not None else None,
                        within_fraction=float(within.mean()), longest_dwell_s=longest/30,
                        endpoint_mean_signed_error_mm=float(error[final,env].mean()*1000),
                        endpoint_max_abs_error_mm=float(np.abs(error[final,env]).max()*1000),
                        endpoint_thumb_action_abs=float(np.abs(trace['action'][final,env,16:]).mean()),
                        endpoint_thumb_target_change_rad=float(np.abs(np.diff(trace['target'][final,env,16:],axis=0)).mean()),
                        endpoint_thumb_tracking_error_rad=float(np.abs(trace['target'][final,env,16:]-trace['q'][final,env,16:]).mean()),
                        endpoint_thumb_contact_fraction=float((trace['contact'][final,env,0]>0).mean()),
                        endpoint_body_stable=bool((trace['drift'][final,env]<.01).all() and (trace['rotation'][final,env]<.25).all())))
            subset=[row for row in records if row['source']==source and row['protocol']==f'fixed{seconds}']
            attained=[row for row in subset if row['attained_300ms']]
            failed=[row for row in subset if not row['final_300ms']]
            summaries.append(dict(source=source,protocol=f'fixed{seconds}',episodes=32,stages=len(subset),
                strict_episodes=report['stable_full_all_endpoints'],alive_episodes=report['alive_full'],
                attained_stages=len(attained),endpoint_held_stages=sum(row['final_300ms'] for row in subset),
                attained_then_left=sum(row['left_after_attainment'] for row in attained),
                failed_endpoints_body_stable=sum(row['endpoint_body_stable'] for row in failed),
                failed_endpoint_thumb_action_abs_mean=float(np.mean([row['endpoint_thumb_action_abs'] for row in failed])),
                failed_endpoint_thumb_contact_fraction_mean=float(np.mean([row['endpoint_thumb_contact_fraction'] for row in failed])),
                trace_sha256=hashlib.sha256((directory/'trace.npz').read_bytes()).hexdigest(),
                checkpoint_sha256=report['checkpoint_sha256']))
    with (args.output/'stages.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    result=dict(status='existing_frozen_trace_diagnosis',summaries=summaries,
        interpretation='Observed attainment, subsequent departure, actuation and contact proxies do not establish a reward or contact causal mechanism. No checkpoint selected; all original final1000 traces retained.')
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
