"""Record the frozen encoder and actual physics work around student actor PPO."""
import hashlib
import json
import os
from pathlib import Path
from scripts import wuji_goal_common
import torch
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now
from isaacgymenvs.tasks.wuji_fixed_student_actor import WujiFixedStudentActor
from scripts.train_wuji_student_actor import main as train
from rl_games.algos_torch.a2c_continuous import A2CAgent
from scripts.wuji_sapg_kl_metrics import split_kl, summarize_epochs


def main():
    output = Path(os.environ['WUJI_FIXED_STUDENT_AUDIT'])
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'encoder-audit.json').exists()
    instances = []
    original = WujiFixedStudentActor.__init__
    original_gradient = A2CAgent.calc_gradients
    kl_records = []

    def observed_gradient(self, batch):
        original_gradient(self, batch)
        mu, sigma = self.train_result[6:8]
        row = split_kl(mu, sigma, batch['mu'], batch['sigma'], batch.get('rnn_masks'),
                       batch['off_policy_mask'], self.train_result[3])
        row.update(epoch=int(self.epoch_num), minibatch=len(kl_records))
        kl_records.append(row)
        if len(kl_records) % 24 == 0:
            atomic_json(output/'kl-audit.json', dict(records=kl_records, epochs=summarize_epochs(kl_records)))

    def capture(self, *args, **kwargs):
        original(self, *args, **kwargs)
        instances.append((self, tensor_digest(self.fixed_student_encoder.state_dict())))

    WujiFixedStudentActor.__init__ = capture
    A2CAgent.calc_gradients = observed_gradient
    returned = False
    try:
        train()
        returned = True
    finally:
        WujiFixedStudentActor.__init__ = original
        A2CAgent.calc_gradients = original_gradient
        atomic_json(output/'kl-audit.json', dict(records=kl_records, epochs=summarize_epochs(kl_records),
                    reference='Pre-current-step policy versus SAPG minibatch reference, which can refresh within epoch.',
                    training_returned=returned))
        records = []
        for env, before in instances:
            after = tensor_digest(env.fixed_student_encoder.state_dict())
            records.append(dict(num_envs=env.num_envs, control_steps=env.control_steps,
                                physics_transitions=env.control_steps*env.num_envs,
                                student_sha256=env.fixed_student_sha256,
                                encoder_before=before, encoder_after=after,
                                unchanged=before == after,
                                all_parameters_frozen=all(not p.requires_grad for p in env.fixed_student_encoder.parameters()),
                                encoder_in_eval=not env.fixed_student_encoder.training,
                                parameters_finite=all(torch.isfinite(p).all().item() for p in env.fixed_student_encoder.parameters())))
        files = [Path(__file__), Path(__file__).with_name('train_wuji_student_actor.py')]
        record = dict(finished=now(), training_returned=returned, environments=records,
                      source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        atomic_json(output/'encoder-audit.json', record)
        if returned:
            assert records and all(x['unchanged'] and x['all_parameters_frozen'] and x['encoder_in_eval']
                                   and x['parameters_finite'] and x['physics_transitions'] > 0 for x in records)


if __name__ == '__main__':
    main()
