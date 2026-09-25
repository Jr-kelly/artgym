# Wuji 全量项目备份 · 2026-09-25

本机三个项目目录已完整捕获并恢复验证。**远端独有文件尚未覆盖**：此前四卡、八卡及暂存机入口拒绝连接，等待可用SSH后补充远端增量。本Release不能被称为所有机器的最终全量备份。

|项目|数值|
|---|---:|
|普通文件|192,177|
|全部路径（含目录/符号链接）|235,768|
|原始文件总字节|208,190,472,088|
|去重后数据字节|124,289,086,927|
|压缩分卷总字节|115,890,298,627|
|分卷数|225|

包括原仓库、实验副本、早期demo工作树下全部隐藏/忽略文件、Git元数据、未提交代码、资产、初态、原始轨迹、所有本机中间CP、成功及失败实验、日志、缓存与项目tmp。内容相同的64MiB块只存一份，manifest保留每个原始路径；不是精选结果包。操作系统及整个用户HOME不属于此次项目备份范围，已有Python/conda依赖清单附在evidence中。

逐文件捕获开始：2026-09-25T03:26:35.821588+00:00；结束：2026-09-25T03:59:18.711907+00:00。原训练保持运行，采用逐文件读取及第二遍变化核对，活跃日志按读取时长度保存；不是同一瞬间的原子文件系统快照。捕获之后新增训练数据需后续增量备份。

已实际恢复全部192,177个普通文件，核验压缩分卷、内容块及完整文件SHA256。GitHub上传另核验每个资产的服务端digest。

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
