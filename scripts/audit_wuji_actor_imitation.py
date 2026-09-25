"""Keep the strict fixed-clock scorer for a directly action-distilled actor."""
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import torch
from scripts.audit_wuji_student_actor import main as audit


def main():
    checkpoint=Path(sys.argv[sys.argv.index('--checkpoint')+1])
    payload=torch.load(checkpoint,map_location='cpu')
    metadata=payload['imitation']
    assert metadata['loss']=='raw20GaussianmeanMSE'
    assert metadata['rollout']=='student deterministic means only'
    audit()
    output=Path(sys.argv[sys.argv.index('--output')+1])
    path=output/'report.json'
    report=json.loads(path.read_text())
    report.update(policy_kind='student_with_direct_teacher_action_imitation',imitation=metadata,
        scope='Directraw20actionMSE on student-drivenphysicalstates. Frozen temporalencoder and normalization, trainablehead oractor. Teacher labels use separate privileged recurrent history only duringtraining. Noobjecttruth to actor. Same strictfixed20s332development score; notpaperlatentMSE orhardwarevalidation.')
    path.write_text(json.dumps(report,indent=2)+'\n')
    (output/'imitation-audit-source.py').write_bytes(Path(__file__).read_bytes())


if __name__=='__main__':
    main()
