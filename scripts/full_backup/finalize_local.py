#!/usr/bin/env python3
"""Finish local backup verification and GitHub publication; keep remote gaps explicit."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = Path('/data/research/artgym-experiments-20260921')


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(data)
    return h.hexdigest()


def progress(stage, **kwargs):
    value = dict(updated=now(), stage=stage, **kwargs)
    atomic(ROOT / 'finalization-status.json', value)
    print(json.dumps(value, ensure_ascii=False), flush=True)


def alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
    except FileNotFoundError:
        return False


def wait_snapshot():
    while True:
        status = json.loads((ROOT / 'status.json').read_text())
        if status['stage'] == 'snapshot_complete':
            return
        process = json.loads((ROOT / 'snapshot-process.json').read_text())
        if not alive(process['pid']):
            raise RuntimeError('Snapshot stopped before completion; inspect snapshot.log')
        progress('waiting_snapshot', captured_files=status['files_recorded'], compressed_bytes=status['compressed_bytes'])
        time.sleep(30)


def main():
    env = os.environ.copy()
    for k in ['LD_LIBRARY_PATH', 'LD_PRELOAD']:
        env.pop(k, None)
    env['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + env.get('PATH', '')
    wait_snapshot()
    index_path = ROOT / 'wuji-full-backup-20260925-index.json'
    index = json.loads(index_path.read_text())
    assert index['local_snapshot_complete'] and not index['errors']
    findings = json.loads((ROOT / 'credential-findings.json').read_text())
    review_path = ROOT / 'credential-review.json'
    review = json.loads(review_path.read_text()) if review_path.exists() else {}
    assert all(review.get(f["path"] + '|' + str(f["offset"]) + '|' + f["value_sha256"]) == 'public_fixture_or_nonsecret' for f in findings), 'Content review pending'
    restore_receipt = ROOT / 'evidence/full-restore-verification.json'
    if not restore_receipt.exists():
        destination = ROOT / 'restore-audit'
        if destination.exists():
            raise RuntimeError('Incomplete restore directory exists; inspect before retrying')
        progress('restoring_every_local_file', entries=index['entries'], logical_bytes=index['logical_bytes'])
        with (ROOT / 'restore.log').open('w') as log:
            result = subprocess.run([sys.executable, str(ROOT / 'tools/restore.py'), '--backup', str(ROOT),
                                     '--destination', str(destination)], stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError('Full restore failed; see restore.log')
        lines = (ROOT / 'restore.log').read_text().splitlines()
        record = json.loads(lines[-1])
        assert record['status'] == 'verified' and record['restored_files'] == index['files']
        record.update(finished=now(), destination=str(destination),
                      manifest_sha256=index['manifest']['sha256'],
                      scope='Every manifest file restored and verified by whole-file SHA256; all referenced compressed packs and chunks verified.')
        atomic(restore_receipt, record)
    restore = json.loads(restore_receipt.read_text())
    assert restore['manifest_sha256'] == index['manifest']['sha256']
    progress('waiting_pack_uploads', restored_files=restore['restored_files'])
    while not (ROOT / 'upload-packs-complete.json').exists():
        process = json.loads((ROOT / 'upload-process.json').read_text())
        if not alive(process['pid']):
            raise RuntimeError('Uploader stopped before completion; resume uploader first')
        time.sleep(30)
    delivery = ROOT / 'delivery'
    delivery.mkdir(exist_ok=True)
    for path in [index_path, ROOT / index['manifest']['name']]:
        shutil.copy2(path, delivery / path.name)
    for name in ['restore', 'snapshot', 'upload', 'finalize_local']:
        shutil.copy2(ROOT / 'tools' / (name + '.py'), delivery / ('wuji-backup-' + name + '.py'))
    shutil.copy2(ROOT / 'spec.json', delivery / 'wuji-full-backup-20260925-spec.json')
    evidence = delivery / 'wuji-full-backup-20260925-evidence.tar.gz'
    with tarfile.open(evidence, 'w:gz') as archive:
        archive.add(ROOT / 'evidence', arcname='evidence', recursive=True)
        for name in ['credential-findings.json', 'credential-review.json', 'snapshot-process.json', 'upload-process.json']:
            path = ROOT / name
            if path.exists():
                archive.add(path, arcname=name)
    remote_pending = index['remote_pending']
    coverage = dict(created=now(), local_complete=True, all_hosts_complete=not remote_pending,
                    roots=index['roots'], files=index['files'], entries=index['entries'],
                    logical_bytes=index['logical_bytes'], unique_blob_bytes=index['unique_blob_bytes'],
                    compressed_bytes=sum(p['bytes'] for p in index['packs']), packs=len(index['packs']),
                    capture_started=index['started'], capture_finished=index['finished'],
                    restore=restore, remote_pending=remote_pending, consistency=index['consistency'])
    atomic(delivery / 'wuji-full-backup-20260925-coverage.json', coverage)
    readme = f'''# Wuji 全量项目备份 · 2026-09-25

本机三个项目目录已完整捕获并恢复验证。**远端独有文件尚未覆盖**：此前四卡、八卡及暂存机入口拒绝连接，等待可用SSH后补充远端增量。本Release不能被称为所有机器的最终全量备份。

|项目|数值|
|---|---:|
|普通文件|{index['files']:,}|
|全部路径（含目录/符号链接）|{index['entries']:,}|
|原始文件总字节|{index['logical_bytes']:,}|
|去重后数据字节|{index['unique_blob_bytes']:,}|
|压缩分卷总字节|{coverage['compressed_bytes']:,}|
|分卷数|{len(index['packs'])}|

包括原仓库、实验副本、早期demo工作树下全部隐藏/忽略文件、Git元数据、未提交代码、资产、初态、原始轨迹、所有本机中间CP、成功及失败实验、日志、缓存与项目tmp。内容相同的64MiB块只存一份，manifest保留每个原始路径；不是精选结果包。操作系统及整个用户HOME不属于此次项目备份范围，已有Python/conda依赖清单附在evidence中。

逐文件捕获开始：{index['started']}；结束：{index['finished']}。原训练保持运行，采用逐文件读取及第二遍变化核对，活跃日志按读取时长度保存；不是同一瞬间的原子文件系统快照。捕获之后新增训练数据需后续增量备份。

已实际恢复全部{index['files']:,}个普通文件，核验压缩分卷、内容块及完整文件SHA256。GitHub上传另核验每个资产的服务端digest。

## 下载与恢复

需要Python3.10+、zstd、GitHub CLI，以及能容纳压缩包、去重块缓存和恢复目录的磁盘空间。完整恢复时临时缓存默认使用系统TMPDIR；可将TMPDIR设到空间充足的磁盘。

```bash
gh release download wuji-full-backup-20260925-v1 --repo Jr-kelly/artgym --dir wuji-backup
cd wuji-backup
sha256sum -c SHA256SUMS.txt
python3 wuji-backup-restore.py --backup . --destination ../wuji-restored --relocate-internal-links
```

恢复目标必须为空。三个目录恢复为 `wuji-restored/artgym`、`wuji-restored/artgym-experiments-20260921`、`wuji-restored/artgym-wuji-knife-demo`。`--relocate-internal-links`将三个目录之间的绝对符号链接改为恢复目录内的相对链接；省略该选项可逐字保留原链接。源文件中的绝对路径、venv shebang、git worktree路径不会自动重写，换机器运行前应按实际路径调整。仅恢复某目录/文件可重复传入 `--prefix artgym-experiments-20260921/...`；若只做全包验证，使用 `--verify-only`。

不要把备份直接解压覆盖正在运行的训练目录。Git工作树迁移可在新目录执行 `git -C ../wuji-restored/artgym worktree repair ../wuji-restored/artgym-wuji-knife-demo`。

## 可浏览代码与实验索引

[代码分支](https://github.com/Jr-kelly/artgym/tree/backup/wuji-full-20260925) · [研究记录和历史Release索引](https://github.com/Jr-kelly/artgym/tree/backup/wuji-full-20260925/docs/wuji)

本次备份保存了失败方案，不意味着它们全部成功。核心teacher+student仿真开合已完成；真实标定、DR和真机部署仍属后续工作。精细CAD不是当前必做前置项。
'''
    (delivery / 'README.md').write_text(readme)
    checks = [(p['sha256'], p['name']) for p in index['packs']]
    checks += [(sha(p), p.name) for p in sorted(delivery.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt']
    (delivery / 'SHA256SUMS.txt').write_text(''.join(h + '  ' + n + '\n' for h, n in checks))
    release = json.loads((ROOT / 'release.json').read_text())
    progress('uploading_metadata', packs=len(index['packs']))
    subprocess.run([sys.executable, str(ROOT / 'tools/upload.py'), str(ROOT), '--release-id', str(release['id']),
                    '--workers', '8', '--include-metadata', '--once'], check=True)
    pages = json.loads(subprocess.check_output(['gh', 'api', f"repos/Jr-kelly/artgym/releases/{release['id']}/assets?per_page=100",
                                               '--paginate', '--slurp'], env=env, text=True))
    assets = {a['name']: a for page in pages for a in page}
    for digest, name in checks + [(sha(delivery / 'SHA256SUMS.txt'), 'SHA256SUMS.txt')]:
        assert assets[name]['digest'] == 'sha256:' + digest and assets[name]['state'] == 'uploaded', name
    # Publication is already authorized by the user's explicit full-backup request.
    body = dict(draft=False, name='Wuji 全量备份 · 本机完整 / 远端待补 · 2026-09-25', body=readme, make_latest='false')
    request = ROOT / 'publish-request.json'
    atomic(request, body)
    progress('publishing_verified_local_backup', assets=len(assets))
    published = json.loads(subprocess.check_output(['gh', 'api', '--method', 'PATCH',
                           f"repos/Jr-kelly/artgym/releases/{release['id']}", '--input', str(request)], env=env, text=True))
    assert not published['draft']
    # Read back a metadata asset using its public URL and compare bytes.
    url = f"https://github.com/Jr-kelly/artgym/releases/download/{release['tag_name']}/wuji-full-backup-20260925-coverage.json"
    downloaded = ROOT / 'evidence/github-coverage-readback.json'
    subprocess.run(['curl', '-fL', '--silent', '--show-error', '--retry', '3', '--max-time', '90',
                    url, '-o', str(downloaded)], env=env, check=True)
    assert sha(downloaded) == sha(delivery / 'wuji-full-backup-20260925-coverage.json')
    final = dict(completed=now(), status='local_complete_remote_pending' if remote_pending else 'complete',
                 release=published['html_url'], release_id=release['id'], assets=len(assets),
                 github_sha256_all_verified=True, public_metadata_readback_verified=True, **coverage)
    atomic(ROOT / 'FINAL.json', final)
    atomic(EXPERIMENT / 'runs/wuji-goal/diagnostics/full-backup-20260925-v1-final.json', final)
    with (EXPERIMENT / 'runs/wuji-goal/journal/events.jsonl').open('a') as output:
        output.write(json.dumps(dict(event='full_local_backup_published', **final), ensure_ascii=False) + '\n')
    handoff = EXPERIMENT / 'WUJI_GOAL_HANDOFF.md'
    content = handoff.read_text()
    note = f"\n## 全量备份本机部分完成（{now()}）\n\n本机3目录{index['files']}文件/{index['logical_bytes']}字节已完整捕获、全量恢复核验；{len(index['packs'])}分卷及元数据已上传并逐项校验GitHub SHA256，Release {published['html_url']} 。详细完成记录 `/home/agiuser/artgym-full-backup-20260925-v1/FINAL.json` 与 `runs/wuji-goal/diagnostics/full-backup-20260925-v1-final.json`。远端SSH全部拒绝连接，远端独有文件待补，不能称所有机器全量完成；用户新入口到达后先拉取远端差异继续备份。后续新增CP/日志亦需增量。备份README内含下载、恢复、路径迁移说明。\n\n"
    position = content.find('\n## ')
    content = content[:position] + note + content[position:]
    handoff.write_text(content)
    Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md').write_text(content)
    progress(final['status'], release=final['release'], files=index['files'])


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        progress('failed', error=repr(exc))
        raise
