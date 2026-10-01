"""Describe equal-update controls across checkpoints without pooling repeated episodes."""
import csv
import json
import re
from pathlib import Path


def load(root, model):
    directory = root / (model + '-development-analysis')
    if not (directory / 'report.json').exists():
        return None
    report = json.loads((directory / 'report.json').read_text())
    assert report['independent_rescore']
    rows = [r for r in report['rows'] if r['model'] == model]
    if len(rows) != 12 or any(r['n'] != 32 for r in rows):
        return None
    with (directory / 'trials.csv').open() as stream:
        trials = {(r['protocol'], int(r['source']), int(r['trial'])): r
                  for r in csv.DictReader(stream) if r['model'] == model}
    assert len(trials) == 384
    return rows, trials


def main():
    root = Path('research/unified-student-20261001')
    steps = sorted({int(re.search(r'-(\d+)-development-analysis$', p.name).group(1))
                    for p in root.glob('SC-real-*-development-analysis')})
    summaries, cells = [], []
    for intervention, left_prefix, right_prefix, minimum in [
            ('executed_target_loss', 'SC-real', 'SA-real', 6401),
            ('known_controller_input', 'SC-masked', 'SC-real', 3201)]:
        for step in steps:
            if step < minimum:
                continue
            left_name, right_name = left_prefix + '-' + str(step), right_prefix + '-' + str(step)
            left, right = load(root, left_name), load(root, right_name)
            if left is None or right is None:
                continue
            lr, lt = left
            rr, rt = right
            assert lt.keys() == rt.keys()
            assert all(lt[k]['cohort_sha256'] == rt[k]['cohort_sha256'] for k in lt)
            ss_left = [r for r in lr if r['protocol'] != 'F']
            ss_right = [r for r in rr if r['protocol'] != 'F']
            differences = []
            for r in rr:
                reference = next(x for x in lr if x['protocol'] == r['protocol'] and x['source'] == r['source'])
                keys = [k for k in lt if k[:2] == (r['protocol'], r['source'])]
                left_only = sum(lt[k]['success'] == 'True' and rt[k]['success'] == 'False' for k in keys)
                right_only = sum(lt[k]['success'] == 'False' and rt[k]['success'] == 'True' for k in keys)
                assert right_only - left_only == r['success'] - reference['success']
                if r['protocol'] != 'F':
                    differences.append(right_only - left_only)
                cells.append(dict(intervention=intervention, update=step, left=left_name, right=right_name,
                    protocol=r['protocol'], source=r['source'], n=32,
                    left_success=reference['success'], right_success=r['success'],
                    left_only=left_only, right_only=right_only,
                    left_body=reference['body_stable'], right_body=r['body_stable']))
            summaries.append(dict(intervention=intervention, update=step, left=left_name, right=right_name,
                left_worst_S=min(r['success'] for r in ss_left), right_worst_S=min(r['success'] for r in ss_right),
                left_min_S_body=min(r['body_stable'] for r in ss_left), right_min_S_body=min(r['body_stable'] for r in ss_right),
                left_min_stage_hold=min(r['worst_stage_hold'] for r in ss_left), right_min_stage_hold=min(r['worst_stage_hold'] for r in ss_right),
                improved_S_cells=sum(d > 0 for d in differences), worsened_S_cells=sum(d < 0 for d in differences),
                tied_S_cells=sum(d == 0 for d in differences)))
    result = dict(rows=summaries, paired_cells=cells,
        scope='Equal-update checkpoint comparisons of the registered shared-parent controls. All checkpoints reuse the same development episodes; counts across cells/checkpoints are descriptive and must not be pooled as independent samples or optimization seeds. This table does not claim persistent or universal intervention benefit.')
    (root / 'controlled-method-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (root / 'controlled-method-summary.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(json.dumps(dict(matched_checkpoints=len(summaries), source_protocol_pairs=len(cells))))


if __name__ == '__main__':
    main()
