"""Describe attained-then-left behavior from saved fixed-clock physical traces.

This is an offline diagnostic, not a replacement success metric. Extension is
command stage parity, never a threshold on absolute slider coordinates.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def stages(trace, stage_steps):
    valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
    error = trace['slider'] - trace['goal']
    assert error.shape == valid.shape and stage_steps in (60, 150)
    rows = []
    for trial in range(error.shape[1]):
        for start in range(0, 600, stage_steps):
            end = start + stage_steps
            within = (np.abs(error[start:end, trial]) < .002) & valid[start:end, trial]
            streak = longest = 0
            first = None
            for offset, hit in enumerate(within):
                streak = streak + 1 if hit else 0
                longest = max(streak, longest)
                if streak >= 9 and first is None:
                    first = offset
            tail = slice(end-9, end)
            def mean(value):
                return float(value.mean()) if value.size else None
            rows.append(dict(trial=trial, stage=start//stage_steps,
                endpoint='extension' if (start//stage_steps)%2 == 0 else 'retraction',
                recorded_steps=len(within), attained_300ms=first is not None,
                final_300ms=bool(len(within)==stage_steps and within[-9:].all()),
                left_after_attainment=bool(first is not None and (~within[first+1:]).any()),
                first_attainment_s=(first+1)/30 if first is not None else None,
                longest_dwell_s=longest/30,
                endpoint_mean_signed_error_mm=mean(error[tail, trial]*1000),
                endpoint_thumb_action_abs=mean(np.abs(trace['action'][tail, trial, 16:])),
                endpoint_thumb_tracking_error_rad=mean(np.abs(trace['target'][tail, trial, 16:]-trace['q'][tail, trial, 16:])),
                endpoint_thumb_contact_fraction=mean((trace['contact'][tail, trial, 0]>0).astype(float)),
                endpoint_body_stable=bool(len(within)==stage_steps and
                    (trace['drift'][tail, trial]<.01).all() and (trace['rotation'][tail, trial]<.25).all())))
    return rows


def grouped(rows):
    result=[]
    for endpoint in ('extension','retraction'):
        subset=[row for row in rows if row['endpoint']==endpoint]
        failed=[row for row in subset if not row['final_300ms']]
        item=dict(endpoint=endpoint, stages=len(subset),
            attained=sum(row['attained_300ms'] for row in subset),
            final_held=sum(row['final_300ms'] for row in subset),
            attained_then_left=sum(row['left_after_attainment'] for row in subset),
            failed=len(failed), failed_body_stable=sum(row['endpoint_body_stable'] for row in failed))
        for key in ('endpoint_mean_signed_error_mm','endpoint_thumb_action_abs',
                    'endpoint_thumb_tracking_error_rad','endpoint_thumb_contact_fraction'):
            values=[row[key] for row in failed if row[key] is not None]
            item['failed_'+key]=float(np.mean(values)) if values else None
        result.append(item)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--stage-seconds',type=int,choices=[2,5],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    with np.load(args.trace) as archive:
        rows=stages(archive,args.stage_seconds*30)
    with (args.output/'stages.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    result=dict(trace=str(args.trace),trace_sha256=hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        groups=grouped(rows),scope=__doc__)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
