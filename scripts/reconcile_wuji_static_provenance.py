"""Preserve static reports and append startup-source identity corrections."""
import hashlib,json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    corrections=[]
    for source in (root/'runs/wuji-goal/diagnostics').rglob('source.py'):
        if 'Hold the initialized commanded joint targets' not in source.read_text():continue
        report=source.parent/'report.json'
        if not report.exists():continue
        data=json.loads(report.read_text());actual=hashlib.sha256(source.read_bytes()).hexdigest()
        if actual==data.get('source_sha256'):continue
        row=dict(status='metadata_correction_only',report=str(report.relative_to(root)),
                 report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                 recorded_source_sha256=data.get('source_sha256'),executed_startup_source_sha256=actual,
                 source_copy=str(source.relative_to(root)),metrics_unchanged=True,
                 reason='Earlier static auditor hashed the source at shutdown; archived startup bytes identify the executed version.')
        target=source.parent/'provenance-correction.json'
        if target.exists():assert json.loads(target.read_text())==row
        else:target.write_text(json.dumps(row,indent=2)+'\n')
        corrections.append(row)
    (root/'runs/wuji-goal/static-source-provenance-corrections.json').write_text(json.dumps(corrections,indent=2)+'\n')
    print(json.dumps(dict(corrections=len(corrections))))


if __name__=='__main__':main()
