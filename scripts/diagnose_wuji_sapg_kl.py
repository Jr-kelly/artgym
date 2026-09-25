"""Measure SAPG on/off-policy KL with zero optimizer LR, using real rollouts."""
import hashlib
import json
import os
from pathlib import Path
from scripts import wuji_goal_common  # Isaac Gym before torch.
import torch
from rl_games.algos_torch.a2c_continuous import A2CAgent
from rl_games.algos_torch import torch_ext
from scripts.train_wuji_student_actor_audited import main as train
from scripts.monitor_wuji_checkpoints import atomic_json, now


def main():
    out = Path(os.environ['WUJI_KL_DIAGNOSTIC'])
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'status.json').exists()
    atomic_json(out/'status.json', dict(status='running', started=now()))
    original = A2CAgent.calc_gradients
    records = []
    agents = []

    def observed(self, batch):
        assert all(group['lr'] == 0 for group in self.optimizer.param_groups)
        if not agents:
            agents.append((self, {name: p.detach().cpu().clone() for name, p in self.model.named_parameters()}))
        assert agents[0][0] is self
        original(self, batch)
        mu, sigma = self.train_result[6:8]
        with torch.no_grad():
            values = torch_ext.policy_kl(mu, sigma, batch['mu'], batch['sigma'], False)
            masks = batch.get('rnn_masks')
            weights = torch.ones_like(values) if masks is None else masks.reshape(-1)
            valid = weights > 0
            off = batch['off_policy_mask'].reshape(-1)
            assert values.shape == valid.shape == off.shape
            # The upstream helper includes1e-5 in the denominator, so even
            # identical distributions need not produce zero. Record exact
            # float64 Gaussian KL separately; do not rename the old statistic.
            new_mu, new_sigma = mu.double(), sigma.double()
            old_mu, old_sigma = batch['mu'].double(), batch['sigma'].double()
            assert (new_sigma > 0).all() and (old_sigma > 0).all()
            exact = (torch.log(old_sigma/new_sigma) +
                     (new_sigma.square()+(old_mu-new_mu).square())/(2*old_sigma.square())-.5).sum(-1)
            reconstructed = (values * weights).sum()/valid.numel()
            assert torch.allclose(reconstructed, self.train_result[3], atol=1e-6, rtol=1e-6)
            row = dict(epoch=int(self.epoch_num), minibatch=len(records),
                       reported_kl=float(self.train_result[3]), samples=int(valid.sum()),
                       model_forward_precedes_optimizer=True)
            for name, mask in [('on', valid & ~off), ('off', valid & off)]:
                v = values[mask]
                precise = exact[mask]
                row[name] = dict(count=int(mask.sum()), upstream_mean=float(v.mean()) if len(v) else None,
                                 upstream_maximum=float(v.max()) if len(v) else None,
                                 exact_gaussian_mean=float(precise.mean()) if len(v) else None,
                                 exact_gaussian_maximum=float(precise.max()) if len(v) else None)
            records.append(row)
            if len(records) % 20 == 0:
                atomic_json(out/'minibatches.json', records)

    A2CAgent.calc_gradients = observed
    try:
        train()
        assert records and {x['epoch'] for x in records} == {1,2,3}
        agent, before = agents[0]
        parameters = {name: torch.equal(p.detach().cpu(), before[name]) for name, p in agent.model.named_parameters()}
        atomic_json(out/'parameter-invariance.json', dict(all_unchanged=all(parameters.values()), parameters=parameters,
                    scope='All model named parameters from first gradient call through training return; compare final checkpoint to initialization separately.'))
        assert parameters and all(parameters.values())
        atomic_json(out/'minibatches.json', records)
        atomic_json(out/'status.json', dict(status='completed', returncode=0, finished=now(),
                    minibatches=len(records), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    note='All optimizer LR0. Actor parameter invariance requires final checkpoint comparison; this is a diagnostic, not training progress.'))
    except BaseException as error:
        atomic_json(out/'status.json', dict(status='failed', error=repr(error), finished=now()))
        raise
    finally:
        A2CAgent.calc_gradients = original


if __name__ == '__main__':
    main()
