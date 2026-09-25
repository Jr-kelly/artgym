"""Compare inherited import inertia with the authored mass-consistent boxes.

This is a new physics sensitivity profile, not calibrated hardware inertia.
No model, mass, control, geometry, observations, or success criterion changes.
The source URDF's nominal mass matches the configured body masses.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from scripts import audit_wuji_timed_commands as evaluator
import numpy as np
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inertia-mode',choices=['imported','authored'],required=True)
    args,remaining=parser.parse_known_args()
    output=Path(remaining[remaining.index('--output')+1])
    root=Path(__file__).resolve().parents[1]
    source=root/'assets/objects/knife_wuji_demo_aligned/000/mobility.urdf'
    tree=ET.parse(source)
    modes={}
    for link in tree.findall('link'):
        size=np.fromstring(link.find('collision/geometry/box').get('size'),sep=' ')
        mass=float(link.find('inertial/mass').get('value'))
        inertia=mass/12*(sum(size**2)-size**2)
        authored=np.array([float(link.find('inertial/inertia').get(k)) for k in ['ixx','iyy','izz']])
        assert np.allclose(inertia,authored,rtol=1e-12,atol=1e-14)
        modes[link.get('name')]=dict(mass=mass,authored=authored.tolist(),
            imported=(inertia*float(np.prod(size)*1000)/mass).tolist())
    record=dict(scope=__doc__,mode=args.inertia_mode,expected=modes,source_urdf_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    capture={};factory=evaluator.make_player
    def make_player(cfg,checkpoint):
        env,player=factory(cfg,checkpoint)
        player.model.eval()
        capture.update(model=player.model,before=tensor_digest(player.model.state_dict()))
        record['actual']=[]
        for index in [0,env.num_envs-1]:
            handle=env.gym.find_actor_handle(env.envs[index],'object')
            props=env.gym.get_actor_rigid_body_properties(env.envs[index],handle)
            names=env.gym.get_actor_rigid_body_names(env.envs[index],handle)
            bodies=[]
            for name,body in zip(names,props):
                expected=modes[name]
                diag=[body.inertia.x.x,body.inertia.y.y,body.inertia.z.z]
                assert np.isclose(body.mass,expected['mass'],rtol=1e-5,atol=1e-7)
                assert np.allclose(diag,expected[args.inertia_mode],rtol=1e-5,atol=1e-11),(diag,expected)
                bodies.append(dict(name=name,mass=body.mass,inertia=diag))
            record['actual'].append(dict(env=index,bodies=bodies))
        return env,player
    argv=sys.argv;evaluator.make_player=make_player
    try:
        assert '--object' not in remaining
        profile='knife_wuji_precision_near01' if args.inertia_mode=='imported' else 'knife_wuji_precision_authored_inertia'
        sys.argv=[argv[0]]+remaining+['--object',profile]
        evaluator.main()
        assert capture['before']==tensor_digest(capture['model'].state_dict())
        record.update(status='passed',model_unchanged=True,sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),root/'isaacgymenvs/tasks/artmanip.py',root/'isaacgymenvs/cfg/object/knife_wuji_precision_authored_inertia.yaml']})
        (output/'inertia-report.json').write_text(json.dumps(record,indent=2)+'\n')
        (output/'inertia-source.py').write_bytes(Path(__file__).read_bytes())
        print(json.dumps(record),flush=True)
    finally:
        evaluator.make_player=factory;sys.argv=argv


if __name__=='__main__':main()
