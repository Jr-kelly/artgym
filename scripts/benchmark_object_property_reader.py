"""Read-only candidate benchmark in a real simulator; preserves original readers."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_env
from scripts.batched_object_properties import read_object_properties_batched
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--envs',type=int,default=1000)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cfg=configuration('artmanip_paper_reference',a.envs,['hand=sharpa','object=knife_sharpa_official','test=False'],train='paperReferenceSAPG',seed=4040)
    (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env=make_env(cfg);fields=['object_mass','object_friction','object_dof_damping','object_dof_stiffness'];runs=[]
    try:
        for randomized in [True, False]:
            env.randomize=randomized;reference=None
            for label in ['original','candidate','original','candidate']:
                numpy_state=np.random.get_state();torch_state=torch.get_rng_state();cuda_state=torch.cuda.get_rng_state()
                torch.cuda.synchronize();started=time.perf_counter()
                if label=='original':env._get_object_props()
                else:read_object_properties_batched(env)
                torch.cuda.synchronize();seconds=time.perf_counter()-started
                actual={key:getattr(env,key).clone() for key in fields}
                if reference is None:reference=actual
                for key in fields:torch.testing.assert_close(actual[key],reference[key],rtol=0,atol=0)
                assert torch.equal(torch_state,torch.get_rng_state()) and torch.equal(cuda_state,torch.cuda.get_rng_state())
                after=np.random.get_state();assert all(np.array_equal(x,y) for x,y in zip(numpy_state,after))
                row=dict(reader=label,randomized=randomized,seconds=seconds,bitwise_equal=True,rng_unchanged=True);runs.append(row);print(json.dumps(row),flush=True)
        report=dict(envs=a.envs,arms=runs,
            candidate_sha256=hashlib.sha256((Path(__file__).parent/'batched_object_properties.py').read_bytes()).hexdigest(),
            scope='Same simulator physical properties read repeatedly. Does not benchmark end-to-end training or guarantee bitwise training trajectories. No live teacher modified.')
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
