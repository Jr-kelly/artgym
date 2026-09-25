"""Closed-loop affine student calibration, without privileged inference inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
from isaacgymenvs import infer_student_impl
from scripts.audit_distillation_runtime import tensor_digest
import torch
from torch import nn


class CalibratedStudent(nn.Module):
    def __init__(self,student,record,identity):
        super().__init__();self.student=student;self.identity=identity;self.calls=0
        self.register_buffer('weight',torch.tensor(record['selected']['weight'],dtype=torch.float32))
        self.register_buffer('bias',torch.tensor(record['selected']['bias'],dtype=torch.float32))

    def forward(self,observations):
        predicted=self.student(observations)
        self.calls+=1
        # No environment, privileged observations, teacher encoder, or labels.
        return predicted if self.identity else predicted@self.weight+self.bias


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--calibration-mode',choices=['identity','affine'],required=True)
    args,remaining=parser.parse_known_args()
    record=json.loads(args.calibration.read_text());assert record['status']=='frozen'
    checkpoint=Path(remaining[remaining.index('--checkpoint')+1])
    student=Path(remaining[remaining.index('--student-artifact')+1])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(checkpoint)==record['teacher_sha256'] and sha(student)==record['student_sha256']
    build=infer_student_impl.build_student_encoder_from_artifact;capture={}
    def wrapped(*arguments,**keywords):
        result=build(*arguments,**keywords)
        encoder=CalibratedStudent(result[0],record,args.calibration_mode=='identity').to(next(result[0].parameters()).device)
        encoder.eval();capture['encoder']=encoder
        return (encoder,)+tuple(result[1:])
    infer_student_impl.build_student_encoder_from_artifact=wrapped
    from scripts import audit_wuji_timed_commands as evaluator
    loop=evaluator.run_grasp_evaluation_loop
    def audited_loop(player,env,**kwargs):
        before=tensor_digest(player.model.state_dict())
        # Inference module contains only the restricted encoder and constant
        # fitted coefficients. The frozen teacher encoder is not a child.
        assert set(dict(capture['encoder'].named_children()))=={'student'}
        result=loop(player,env,**kwargs)
        assert tensor_digest(player.model.state_dict())==before
        capture['frozen']=True
        return result
    evaluator.run_grasp_evaluation_loop=audited_loop
    argv=sys.argv
    try:
        sys.argv=[argv[0]]+remaining
        evaluator.main()
        assert capture['frozen'] and capture['encoder'].calls==600
        output=Path(remaining[remaining.index('--output')+1])
        result=dict(status='passed',scope=__doc__,mode=args.calibration_mode,calibration_sha256=sha(args.calibration),
            teacher_sha256=record['teacher_sha256'],base_student_sha256=record['student_sha256'],
            model_unchanged=True,privileged_inputs_to_calibration=False,physical_control_steps=600,source_sha256=sha(Path(__file__)))
        (output/'calibration-report.json').write_text(json.dumps(result,indent=2)+'\n')
        (output/'calibration-source.py').write_bytes(Path(__file__).read_bytes())
    finally:
        infer_student_impl.build_student_encoder_from_artifact=build;evaluator.run_grasp_evaluation_loop=loop;sys.argv=argv


if __name__=='__main__':main()
