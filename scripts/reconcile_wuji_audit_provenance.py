"""Add explicit provenance corrections without changing immutable audit reports.

Earlier timed audits copied their source at startup but read the source hash
again at shutdown. An on-disk update during a run could make the recorded hash
refer to a later version. The archived startup copy is the execution evidence.
"""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    records = []
    for source in sorted((root/"runs/wuji-goal/verification").glob("*/source.py")):
        report = source.parent/"report.json"
        status = source.parent/"status.json"
        if not report.exists() or not status.exists():
            continue
        if json.loads(status.read_text()).get("status") != "completed":
            continue
        data = json.loads(report.read_text())
        if "source_sha256" not in data:
            continue
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual == data["source_sha256"]:
            continue
        record = dict(run=source.parent.name, status="metadata_correction_only",
            original_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
            original_recorded_source_sha256=data["source_sha256"],
            executed_startup_source_copy_sha256=actual,
            source_copy=str(source.relative_to(root)),
            reason=__doc__, metrics_unchanged=True)
        target = source.parent/"provenance-correction.json"
        if target.exists():
            assert json.loads(target.read_text()) == record
        else:
            target.write_text(json.dumps(record, indent=2)+"\n")
        records.append(record)
    target = root/"runs/wuji-goal/audit-source-provenance-corrections.json"
    target.write_text(json.dumps(dict(records=records, scope=__doc__), indent=2)+"\n")
    print(json.dumps(dict(corrections=len(records), runs=[x["run"] for x in records])))


if __name__ == "__main__":
    main()
