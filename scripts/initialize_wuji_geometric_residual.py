"""Zero residual around a verified, shared rolling-thumb reference.

No training or physics result is claimed. Reuse the parent critic/hidden layers,
zero the actor output and start a fresh optimizer and interaction accounting.
"""
import argparse, json, hashlib
from pathlib import Path
from isaacgym import gymapi
from scripts.wuji_robust_learning import ResidualActorCritic, R800, TEACHER
import torch
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seed', type=int, default=2026100353)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    parent = torch.load(a.parent, map_location='cpu')
    reference = json.loads(a.reference.read_text())
    assert reference['all_feasible']
    model = ResidualActorCritic()
    model.load_state_dict(parent['model'])
    torch.nn.init.zeros_(model.actor[-1].weight)
    torch.nn.init.zeros_(model.actor[-1].bias)
    model.logstd.data.fill_(-3.)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4, eps=1e-5)
    report = dict(parent_sha256=hashlib.sha256(a.parent.read_bytes()).hexdigest(),
                  reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),
                  initialization='Inherited critic/hidden layers; exactly zero actor output, logstd-3, fresh Adam; no new fitting',
                  controller='Known task clock and initial issued targets; same calibrated path for every physical asset; no live object/contact input',
                  scope='Controller initialization only; no geometry generalization claim')
    payload = dict(parent)
    payload.update(model=model.state_dict(), optimizer=optimizer.state_dict(),
                   updates=0, transitions=0, args=vars(a), action_base_mode='geometric',
                   action_scale=[.25]*20, thumb_reference=reference,
                   reference_initialization=report, rng_cpu=torch.get_rng_state(),
                   rng_cuda=torch.cuda.get_rng_state_all(), rng_numpy=np.random.get_state(),
                   teacher_sha256=hashlib.sha256(TEACHER.read_bytes()).hexdigest(),
                   student_sha256=hashlib.sha256(R800.read_bytes()).hexdigest())
    path=a.output/'geometric_reference.pth';torch.save(payload,path)
    report['checkpoint_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix('.sha256').write_text(report['checkpoint_sha256']+'\n')
    (a.output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':main()
