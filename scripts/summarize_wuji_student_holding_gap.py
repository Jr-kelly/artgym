"""Describe endpoint margins and joint-target errors from an exact diagnostic replay."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--parity-audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.parity_audit.read_text())
    assert audit['attributable_to_original'] and all(audit['trajectory_exact_parity'].values())
    assert hashlib.sha256((args.diagnostic / 'trace.npz').read_bytes()).hexdigest() == audit['diagnostic_trace_sha256']
    report = json.loads((args.diagnostic / 'report.json').read_text())
    assert report['protocol']['kind'] == 'S'
    with np.load(args.diagnostic / 'trace.npz') as data:
        trace = {key: data[key] for key in data.files}
    probes = torch.load(args.diagnostic / 'latent-probes.pth', map_location='cpu')
    steps, total = trace['active'].shape
    assert total % 4 == 0 and steps == 600
    n = total // 4
    period = report['protocol']['stage_steps']
    valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
    error = np.abs(trace['slider'] - trace['goal'])
    rows = []
    joint_rows = []
    for source in range(4):
        ids = slice(source * n, (source + 1) * n)
        for stage, start in enumerate(range(0, steps, period)):
            end = start + period
            window = error[end - 9:end, ids]
            alive = valid[end - 9:end, ids].all(0)
            peak = window.max(0)
            held = alive & (peak < .002)
            rows.append(dict(source=source, stage=stage, direction='open' if stage % 2 == 0 else 'close',
                             n=n, held=int(held.sum()), valid_last9=int(alive.sum()),
                             last9_peak_error_mm_quantiles=np.quantile(peak, [0, .25, .5, .75, 1]).tolist(),
                             valid_but_failed=int((alive & ~held).sum()),
                             failed_within_3mm=int((alive & ~held & (peak < .003)).sum()),
                             failed_within_5mm=int((alive & ~held & (peak < .005)).sum())))
            rows[-1]['last9_peak_error_mm_quantiles'] = [1000 * x for x in rows[-1]['last9_peak_error_mm_quantiles']]
        squared = []
        max_abs = []
        for probe in probes:
            active = probe['active'][ids].bool()
            differences = (probe['student_target'][ids] - probe['teacher_target'][ids])[active]
            if len(differences):
                squared.append(differences.square())
                max_abs.append(differences.abs())
        squared = torch.cat(squared)
        max_abs = torch.cat(max_abs)
        joint_rows.append(dict(source=source, correlated_time_episode_samples=len(squared),
                               target_rms_rad_per_joint=squared.mean(0).sqrt().tolist(),
                               target_max_abs_rad_per_joint=max_abs.max(0).values.tolist(),
                               mean_over_joints_target_mse_rad2=float(squared.mean())))
    args.output.write_text(json.dumps(dict(parity_audit=str(args.parity_audit),
                                          checkpoint_sha256=report['unified_student_sha256'],
                                          endpoint_rows=rows, joint_target_rows=joint_rows,
                                          scope='Descriptive diagnostics on already-scored development episodes. The actual strict tolerance remains2mm;3/5mm counts describe margins, not alternate success criteria. Joint indices follow the original20-action order. Correlated snapshots are not independent samples; errors do not establish causal attribution.'), indent=2) + '\n')
    print(json.dumps(dict(endpoint_cells=len(rows), source_joint_summaries=len(joint_rows))))


if __name__ == '__main__':
    main()
