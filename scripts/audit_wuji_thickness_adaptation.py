"""Evaluate a named geometry with actual authored box inertia and frozen model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import audit_wuji_timed_commands as evaluator
from scripts.audit_distillation_runtime import tensor_digest
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',required=True);args,remaining=parser.parse_known_args()
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'runs/wuji-goal/geometry-sensitivity-20260922/manifest.json').read_text())
    variant=manifest['variants'][args.variant]
    for p,h in variant['artifact_sha256'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h
    factory=evaluator.make_player;capture={};record=dict(scope=__doc__,variant=args.variant,properties=[])
    def make_player(cfg,cp):
        env,player=factory(cfg,cp);player.model.eval()
        capture.update(model=player.model,before=tensor_digest(player.model.state_dict()))
        assert not cfg.object.asset.override_inertia
        dims=[np.array(variant['parameters']['handle_size']),np.array(variant['parameters']['slider_size'])]
        assert np.allclose(env.instance_link0_bbx.cpu().numpy(),dims[0])
        for row in [0,env.num_envs-1]:
            handle=env.gym.find_actor_handle(env.envs[row],'object')
            bodies=env.gym.get_actor_rigid_body_properties(env.envs[row],handle)
            for b,m,d in zip(bodies,[.029,.006],dims):
                inertia=[b.inertia.x.x,b.inertia.y.y,b.inertia.z.z]
                assert np.isclose(b.mass,m,rtol=1e-5) and np.allclose(inertia,m/12*(sum(d*d)-d*d),rtol=1e-5,atol=1e-11)
                record['properties'].append(dict(env=row,mass=b.mass,inertia=inertia))
        return env,player
    argv=sys.argv;evaluator.make_player=make_player
    try:
        assert '--object' not in remaining
        sys.argv=[argv[0]]+remaining+['--object','knife_wuji_geometry_'+args.variant+'_authored']
        evaluator.main()
        assert tensor_digest(capture['model'].state_dict())==capture['before']
        record.update(status='passed',model_unchanged=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        output=Path(remaining[remaining.index('--output')+1])
        (output/'geometry-adaptation-report.json').write_text(json.dumps(record,indent=2)+'\n')
        (output/'geometry-adaptation-source.py').write_bytes(Path(__file__).read_bytes())
    finally:evaluator.make_player=factory;sys.argv=argv


if __name__=='__main__': main()
