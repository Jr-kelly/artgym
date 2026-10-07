"""Use native contacts preceding the selected actual development frame."""
import json
from pathlib import Path
import numpy as np


def source_contacts(source, window_s=.3):
    manifest = json.loads((Path(source) / 'manifest.json').read_text())
    trace_path = Path(manifest['source'])
    with np.load(trace_path) as trace:
        time_s = float(trace['time'][manifest['takeover_index']])
    rows = [json.loads(line) for line in
            (trace_path.parent / 'wrap-contact-physical-steps.jsonl').open()]
    selected = [row for row in rows
                if time_s-window_s < row['time_s'] <= time_s+1e-7]
    if not selected:
        raise ValueError('No native contacts before selected source frame')
    return trace_path.parent, selected, time_s
