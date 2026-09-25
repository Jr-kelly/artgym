"""Preserve an immutable, self-verified source archive for the isolated experiments."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    root = Path(__file__).resolve().parents[1]
    current = root/'source_manifest.json'
    previous = json.loads(current.read_text())
    paths = set(previous)
    for folder in ['scripts', 'tests', 'isaacgymenvs', 'rl_games', 'make_data', 'func_lygra']:
        for file in (root/folder).rglob('*'):
            if file.is_file() and file.suffix in ('.py', '.yaml', '.yml', '.json', '.md', '.sh'):
                if not {'.git', '__pycache__'}.intersection(file.parts):
                    paths.add(str(file.relative_to(root)))
    paths.update(str(p.relative_to(root)) for p in root.glob('*.md'))
    paths.update(str(p.relative_to(root)) for p in root.glob('*monitor*.json'))
    paths.update(str(p.relative_to(root)) for p in root.glob('*suite.json'))
    paths.update(str(p.relative_to(root)) for p in (root/'runs/wuji-goal/journal').glob('*.jsonl'))
    for pattern in ['handoff-*-spec.json', 'student-*-spec.json', 'rgb-*-spec.json', 'reset-*-spec.json', 'reset-*-queue.json', 'termination-*-spec.json', 'termination-*-queue.json', 'sharpa-*-spec.json', 'teacher-input-probe-*-spec.json', 'teacher-sensor-*-spec.json',
                    'action-label-probe-*-spec.json', 'audit-queue-*.json', '*spec-clarification.json', '*-proposal.json',
                    '*-dataset-manifest.json', '*evaluation-states/manifest.json',
                    '*frame-eval-states/manifest.json', '*fresh100*/manifest.json', '*fresh200*/manifest.json',
                    'frozen-candidates/*/manifest.json']:
        paths.update(str(p.relative_to(root)) for p in (root/'runs/wuji-goal').glob(pattern))
    paths.update(str(p.relative_to(root)) for p in (root/'runs/wuji-goal/research').glob('*.md'))
    for package in (root/'runs/wuji-goal/research').glob('wuji-vision-pinned-*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        for item in json.loads(package.read_text())['files']:
            source = package.parent/item['path']
            assert hashlib.sha256(source.read_bytes()).hexdigest() == item['sha256']
            paths.add(str(source.relative_to(root)))
    # Preserve the small endpoint/body decomposition and its exact program;
    # the complete evaluation traces are in the separately published evidence.
    for pattern in ['early-failure-*.json', 'analyze-early-failures-*.py', 'termination-*.json', 'termination-*/*.json', 'prepare-termination-*.py', 'prepare-host-tool-*.py', 'host-tool-*.json', 'host-tool-*/*.json', 'check-termination-*.py', 'normalizer-frozen-*.json', 'release-termination-*-verified.json',
                    'reset-*.json', 'handoff-*.json', 'release-continuation-*/*.json', 'release-continuation-*.json', 'release-reset-*-verified.json', 'reset-oracle-*.json', 'reset-range-*.json', 'reset-mechanism-*.json', 'reset-range-*.py', 'prepare-reset-*.py', 'prepare-release-*.py', 'reset-*/analysis.json', 'reset-range-control-analysis-*/*.json', 'reset-range-control-analysis-*/*.py', 'finalize-reset-*.py', 'monitor-reset-*.py', 'expand-after-seed2-*.py', 'actor-noise-final-endpoints-*.py', 'actor-noise-final-endpoints-*.json',
                    'actor-noise-drift-*.json', 'pose1-final-rescored-*.json',
                    'actionimit-*.json', 'action-label-analysis-*.json', 'jointimit-*.json',
                    'teacher-input-final-*.json', 'state-estimator-*-audit.json',
                    'teacher-sensor-*-rescored-*.json', 'state-v3-*-rescored-*.json',
                    'state-estimator-v2-stale-history-stop-*.json', 'sharpa-student-cp*-rescored-*.json',
                    'fitted-*-rescored-*.json', 'state-replay-gates-*.json', 'state-replay-current-eval-handoff-*.json',
                    'state-replay-*-rescored-*.json', 'state-replay-rescored-*.json',
                    'state-components-*-rescored-*.json', 'state-components-rescored-*.json',
                    'state-clock-transfer-*.json', 'state-endpoint-bias-*-v2.json',
                    'state-aggregation-*.json',
                    'state-memory-*.json', 'slider-components-*.json', 'slider-components-*.py',
                    'slider-fusion-*.json', 'kinematic-slider-*.json',
                    'controller-history-*.json', 'transfer-command-typo-*.json',
                    'command-slider-*.json', 'sharpa-*-latest-priority-handoff-*.json',
                    'command-slider-inference-*-source.py', 'teacher-absolute-target-variation-*.json',
                    'sharpa-four-student-final-priority-*.json', 'sharpa-eight-capacity-handoff-*.json',
                    'sharpa-four-pool-restored-*.json', 'absolute-target-fit-audit-*.json',
                    'package-absolute-target-runtime-*.py', 'absolute-target-final-rescored-*.json',
                    'sharpa-final100-rescored-*.json', 'command-dagger-*-launch.json',
                    'command-dagger-*-rescored-*.json', 'command-dagger-pair-final-audit-*.json',
                    'rgb-fit-independent-audit-*.json', 'rgb-policy-*-rescored-*.json',
                    'rgb-sensor-*-rescored-*.json', 'rgb-sensor-discrepancy-replay-*.json',
                    'prepare-sensor-*.py', 'queue-sensor-*.py', 'reserve-eight-gpu0-*.py', 'finalize-sensor-port-*.py',
                    'rgb-audit-monitor-corrections-*.json', 'pin-copy-runs-link-failure-*.json',
                    'command-dagger-*/status.json', 'host-resumption-*.json',
                    'evaluation-capacity-*/proposal.json', 'evaluation-capacity-*/student-final-priority.json',
                    'evaluation-priority-*/proposal.json',
                    'sharpa-corrected-evaluation-capacity-*.json',
                    'state-latest-completed-rescored-*.json', 'evaluation-capacity-*/monitor-handoff.json',
                    'sharpa-matched-*.json', 'sharpa-top5-selection-*.json',
                    'sharpa-latest-backlog-*-proposal.json']:
        paths.update(str(p.relative_to(root)) for p in (root/'runs/wuji-goal/diagnostics').glob(pattern))
    for folder in ['assets/hands/sharpa', 'assets/objects/knife_sharpa_official',
                   'caches/initial_grasp/sharpa/knife_sharpa_official']:
        paths.update(str(p.relative_to(root)) for p in (root/folder).rglob('*') if p.is_file())
    # Small, frozen diagnostic geometry packages include their exact assets,
    # caches and initial states; source alone would not reproduce these tests.
    for package in (root/'runs/wuji-goal').glob('geometry-sensitivity-*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        geometry = json.loads(package.read_text())
        for variant in geometry['variants'].values():
            paths.update(variant['artifact_sha256'])
            paths.add(variant['states'])
    for thickness in (root/'runs/wuji-goal').glob('thickness3*-dataset-manifest.json'):
        paths.add(str(thickness.relative_to(root)))
        paths.update(json.loads(thickness.read_text())['artifact_sha256'])
    rootless = root/'runs/wuji-goal/sharpa-rootless-dataset-manifest.json'
    if rootless.exists():
        paths.add(str(rootless.relative_to(root)))
        paths.update(json.loads(rootless.read_text())['artifact_sha256'])
    for package in (root/'runs/wuji-goal').glob('student-calibration-*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        paths.add(str(package.with_name('initial_states.npy').relative_to(root)))
    for package in (root/'runs/wuji-goal').glob('bridge3-fresh*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        paths.update(str(p.relative_to(root)) for p in package.parent.glob('*.npy'))
    for package in (root/'runs/wuji-goal').glob('rgb-fresh*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        paths.update(str(p.relative_to(root)) for p in package.parent.glob('*.npy'))
        paths.update(str(p.relative_to(root)) for p in package.parent.glob('*.json'))
    for package in (root/'runs/wuji-goal').glob('rgb-wider*/manifest.json'):
        paths.add(str(package.relative_to(root)))
        paths.update(str(p.relative_to(root)) for p in package.parent.glob('*.npy'))
        paths.update(str(p.relative_to(root)) for p in package.parent.glob('*.json'))
    paths.add('runs/wuji-goal/goal-state.json')
    for pattern in ['rgb-fresh-*-proposal.json','rgb-fresh-*-candidates.json']:
        paths.update(str(p.relative_to(root)) for p in (root/'runs/wuji-goal').glob(pattern))
    for artifact in (root/'runs/wuji-goal/frozen-candidates').glob('student-cp500-affine-calibration-*/calibration.json'):
        paths.add(str(artifact.relative_to(root)))
    # Never silently drop a previously tracked source path.
    missing = [name for name in paths if not (root/name).is_file()]
    if missing:
        raise FileNotFoundError(repr(missing))
    # Read each file once. A health heartbeat or journal append may happen
    # while archiving; archive the observed bytes without rereading live files.
    snapshot_data = {name: (root/name).read_bytes() for name in sorted(paths)}
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in snapshot_data.items()}
    stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    history = root/'runs/wuji-goal/source-history'
    history.mkdir(parents=True, exist_ok=True)
    old = history/('manifest-before-'+stamp+'.json')
    old.write_bytes(current.read_bytes())
    new = history/('source-manifest-'+stamp+'.json')
    new.write_text(json.dumps(manifest, indent=2)+'\n')
    archive = history/('source-snapshot-'+stamp+'.tar.gz')
    with tarfile.open(str(archive), 'w:gz') as tar:
        for name, data in snapshot_data.items():
            info=tarfile.TarInfo(name);info.size=len(data)
            info.mode=(root/name).stat().st_mode & 0o777
            tar.addfile(info,io.BytesIO(data))
    with tarfile.open(str(archive), 'r|gz') as tar:
        seen = set()
        for entry in tar:
            assert entry.isfile() and entry.name in manifest and entry.name not in seen
            assert hashlib.sha256(tar.extractfile(entry).read()).hexdigest() == manifest[entry.name], entry.name
            seen.add(entry.name)
        assert seen == set(manifest)
    current.write_bytes(new.read_bytes())
    sync = root/'runs/wuji-goal/source-sync-files.txt'
    # Status files are historical evidence in the archive, never source to push
    # over a running process's live status on a shared filesystem.
    sync_exclusions = [name for name in sorted(manifest)
                       if (name.startswith('runs/') and Path(name).name.endswith('status.json'))
                       or ('/' not in name and 'monitor' in name and name.endswith('.json'))]
    sync.write_text('\n'.join(name for name in sorted(manifest) if name not in sync_exclusions)
                   +'\nsource_manifest.json\n')
    result = dict(files=len(manifest), snapshot=str(archive.relative_to(root)),
                  snapshot_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  manifest=str(new.relative_to(root)),
                  manifest_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
                  archive_contents_verified=True, synchronization_exclusions=sync_exclusions)
    (history/('source-snapshot-'+stamp+'-verification.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
