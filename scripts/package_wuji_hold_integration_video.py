"""Preserve actual integration renders, per-source scores, and inspection sheets."""
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    research = ROOT/'research/hold-20260929'
    result = json.loads((research/'video/integration-render-results.json').read_text())
    assert result['status'] == 'completed'
    manifest = []
    for item in result['results']:
        name = 'video-integration-'+item['condition']+'-fixed5'
        source = ROOT/'runs/hold-20260929'/name
        destination = research/'video'/name
        assert not destination.exists()
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('trace.npz', '*.mp4'))
        video = ROOT/'videos'/('hold-integration-'+item['condition']+'-fixed5.mp4')
        assert not video.exists()
        shutil.copy2(source/'evidence/policy.mp4', video)
        sheet = research/'video'/(name+'-contact-sheet.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf',
                        "select='eq(n,0)+eq(n,149)+eq(n,299)+eq(n,449)+eq(n,599)',scale=640:-1,tile=5x1",
                        '-frames:v', '1', '-update', '1', str(sheet)], check=True)
        files = [dict(path=str(path.relative_to(ROOT)), sha256=sha(path))
                 for path in sorted(source.rglob('*')) if path.is_file()]
        manifest.append(dict(**item, video=str(video.relative_to(ROOT)), video_sha256=sha(video),
                             contact_sheet=str(sheet.relative_to(ROOT)), files=files))
    receipt = research/'video/integration-video-results.json'
    receipt.write_text(json.dumps(dict(results=manifest, source_order=[0, 1, 2, 3],
        frame_indices=[0,149,299,449,599],
        scope='Separate local4090 rendered trials, predeclared first perturbation of each source. All outcomes preserved; videos do not replace frozen512 quantitative results.'), indent=2)+'\n')
    archive = ROOT/'runs/hold-20260929/delivery/wuji-hold-integration-video-raw-evidence.tar.gz'
    with tarfile.open(archive, 'x:gz', compresslevel=1) as tar:
        tar.add(receipt, arcname='manifest.json')
        for item in result['results']:
            directory = 'runs/hold-20260929/video-integration-'+item['condition']+'-fixed5'
            tar.add(ROOT/directory, arcname=directory)
    print(receipt)


if __name__ == '__main__':
    main()
