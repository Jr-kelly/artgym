"""Evaluate a bundled temporal encoder and action-imitation actor in physics."""
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import torch
from scripts.audit_distillation_runtime import tensor_digest


def main():
    checkpoint=Path(sys.argv[sys.argv.index('--checkpoint')+1])
    payload=torch.load(checkpoint,map_location='cpu')
    assert payload['imitation']['scope'] in ('actor','joint')
    assert 'joint_encoder_state_dict' in payload
    original=wuji_goal_common.make_player
    references={}

    def make_player(cfg,path):
        env,player=original(cfg,path)
        encoder=env.fixed_student_encoder
        encoder.load_state_dict(payload['joint_encoder_state_dict'])
        encoder.eval()
        for parameter in encoder.parameters():
            parameter.requires_grad_(False)
        references.update(encoder=encoder,digest=tensor_digest(encoder.state_dict()))
        return env,player

    wuji_goal_common.make_player=make_player
    try:
        from scripts.audit_wuji_actor_imitation import main as audit
        audit()
    finally:
        wuji_goal_common.make_player=original
    assert tensor_digest(references['encoder'].state_dict())==references['digest']
    out=Path(sys.argv[sys.argv.index('--output')+1])
    path=out/'report.json'
    report=json.loads(path.read_text())
    report.update(policy_kind='student_with_joint_encoder_action_imitation',
        initial_student_artifact=report.pop('fixed_student_artifact'),
        initial_student_sha256=report.pop('fixed_student_sha256'),
        encoder_checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        evaluated_encoder_tensor_sha256=references['digest'],
        scope='Bundled learned temporal encoder and actor; 50 frames of measured joints and past actions plus initial information. Encoder and actor trained on direct action labels, teacher with separate privileged RNN history. Student alone controls physics. Same strict fixed-clock development scorer; no current object truth to actor, no independent or hardware claim.')
    path.write_text(json.dumps(report,indent=2)+'\n')
    (out/'joint-imitation-audit-source.py').write_bytes(Path(__file__).read_bytes())


if __name__=='__main__':
    main()
