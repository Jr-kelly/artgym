"""Curate a portable simulation recovery packet; no SDK or private media.

The packet retains repository-relative names and a content manifest. It does
not copy the entire experiment history. Runtime verification must be performed
after extraction; a manifest alone is not a restored-demo result.
"""
import argparse, hashlib, json, tarfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
B = Path('runs/wrap-force-20261004')
D = Path('research/wrap-force-20261004')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def collect(paths):
    files = set()
    for relative in paths:
        path = R / relative
        assert path.exists(), str(path)
        for f in ([path] if path.is_file() else path.rglob('*')):
            if not f.is_file() or any(p in {'.git', '__pycache__'} for p in f.parts):
                continue
            if f.suffix in {'.pyc', '.pyo'} or f.name.startswith('.event'):
                continue
            files.add(f.relative_to(R))
    return sorted(files)


def write_packet(output, name, paths):
    rows = [dict(path=str(p), bytes=(R/p).stat().st_size,
                 sha256=digest(R/p)) for p in collect(paths)]
    manifest = output / (name + '-files.json')
    manifest.write_text(json.dumps(dict(format='wuji-recovery-files-v1',
        scope='Content identity only; licensed Isaac Gym/runtime not redistributed',
        files=rows), indent=2) + '\n')
    archive = output / (name + '.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for row in rows:
            tar.add(R/row['path'], arcname=row['path'], recursive=False)
        tar.add(manifest, arcname='recovery-manifests/'+manifest.name)
    return dict(archive=archive.name, bytes=archive.stat().st_size,
                sha256=digest(archive), files=len(rows), manifest=manifest.name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    runtime = ['scripts', 'isaacgymenvs', 'rl_games',
        'assets/robots/g2_wuji', 'assets/hands/wuji_artbot',
        'assets/objects/knife_wuji_real_size_20261002',
        'assets/objects/knife_wuji_robust_family_20261003',
        'research/geometry-generalization-20261002/BASELINE_PHYSICS.json',
        'research/multigrasp-20260928/data/small.npy',
        'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy',
        'research/robust-knife-family-20261003/data/repaired-seeds.npy',
        'research/robust-knife-family-20261003/real-knife-asset-spec.json',
        str(B/'planning'), str(B/'comparison/pressure080-paired-v3/config.json'),
        str(B/'validation/geometry-assets-v3'),
        str(B/'validation/boundary-assets-v35'),
        str(B/'validation/geometry-inputs-corrected-v3'),
        str(B/'measurement/serial-asset-v4'),
        str(B/'measurement/serial-moving-base-v6/report.json')]
    # Only this round's public text/configs, not the embedded private photos.
    runtime += [str(p.relative_to(R)) for p in (R/D).iterdir()
                if p.is_file() and p.suffix in {'.md', '.json', '.txt'}
                and 'private' not in p.name.lower()]
    learning = [
        'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',
        'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',
        'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth']
    # Resolve the actual frozen command files instead of guessing fallback
    # dependencies from names. Only declared inputs, never output directories.
    input_flags={'--grasp-plan','--table-calibration','--acquisition-path',
        '--handover-calibration','--thumb-reference-override',
        '--postlift-regrasp','--proprioceptive-pressure-config',
        '--support-pressure-config'}
    for freeze in ['FROZEN-WRAP-CONTINUOUS-CANDIDATE-V12.json',
                   'FROZEN-CONTINUOUS-CANDIDATE-V10.json']:
        command=json.loads((R/D/freeze).read_text())['command']
        if isinstance(command,str):
            runtime.append(command);command=json.loads((R/command).read_text())
        if isinstance(command,dict):command=command['command']
        for i,flag in enumerate(command[:-1]):
            if flag in input_flags:runtime.append(command[i+1])
            if flag=='--residual-checkpoint':learning.append(command[i+1])
    for name in ['paired-held-single1-pilot-v1r1', 'paired-held-multi12-pilot-v1r1']:
        folder=B/'train'/name
        learning += [str(folder/file) for file in
                     ['update_000120.pth', 'args.json', 'scene.json', 'config.yaml',
                      'complete.json', 'learning.jsonl', 'training-episodes.jsonl']]
    # Actual training physical slots, not original heldout geometry IDs.
    scene = json.loads((R/B/'train/paired-held-single1-pilot-v1r1/scene.json').read_text())
    runtime += ['assets/objects/knife_wuji_dense_under_20261003/'+sid
                for sid in scene['geometry_slots']]
    for name in ['source1-v1', 'multi12-v1']:
        folder = R/B/'batch'/name
        if folder.exists():
            runtime += [str(p.relative_to(R)) for p in folder.glob('*.json')]
    # Preserve saved failed pilots as explicitly unselected recovery states.
    runtime += [str(B/'remote'),
        str(B/'batch/continuous-source2-pressure-v1/nominal-registry.json'),
        str(B/'batch/continuous-source2-pressure-v1/nominal-schedule.json')]
    for name,step in [('corner-thumb-head-nominal-recovery-v21',12),
                      ('corner-functional-load-pilot-v13r1',44)]:
        folder=B/'train'/name
        learning.append(str(folder/('update_%06d.pth'%step)))
        learning += [str(p.relative_to(R)) for p in (R/folder).iterdir()
                     if p.is_file() and p.suffix in {'.json','.jsonl','.yaml'}]
    packets = [write_packet(a.output, 'wrap-runtime', runtime),
               write_packet(a.output, 'wrap-learning-state', learning)]
    (a.output/'packets.json').write_text(json.dumps(dict(packets=packets,
        real_robot_ran=False, sdk_included=False,
        resume_scope='Model/Adam/RNG saved; resume creates fresh physical episodes, not a bitwise solver continuation'),
        indent=2)+'\n')
    print(json.dumps(packets))


if __name__ == '__main__':
    main()
