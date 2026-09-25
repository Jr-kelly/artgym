# Wuji 美工刀实验与全量备份

这是基于 ArtGym 的 Wuji 迁移代码快照，保留了实验脚本、参数、手与刀具资产以及抓姿数据。它包含研究中的失败方案；冻结成功版本应按下列Release的源码/权重哈希复现。

- [最终teacher + student交付](https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923)：文件前缀 `wuji-core-teacher-student-20260924`。
- [全量备份](https://github.com/Jr-kelly/artgym/releases/tag/wuji-full-backup-20260925-v1)：本机192,177个文件、约208GB已完整捕获并全部恢复校验通过；约116GB/225分卷正在上传，包括日志、原始轨迹、中间CP、失败记录和Git元数据；远端SSH不可用，远端独有文件待补，不能当作全部机器已备份。
- [核心结果](core-teacher-student-final-20260924.md)、[论文差异](paper-alignment-current-20260924.md)、[sim2real建议](sim2real-assessment-20260924.md)、[实验资产索引](release-assets-index.md)、[时间线及接续](WUJI_GOAL_HANDOFF.md)。

已完成的范围：现实尺寸参数化刀具、预置功能抓姿下，Wuji的teacher和纯本体感觉latent student完成伸出/收回。没有真机或未见几何成功声明。当前成功分支物性随机化关闭，真机前建议先做真实标定与DR，精细几何按失败证据决定。

## 恢复全量备份

Release完成后下载全部分卷及manifest/index/恢复脚本，在有Python3.10+和zstd的Linux机器执行Release README中的恢复命令。恢复程序校验每卷、每块及每文件SHA256；目标目录必须为空。内容去重只减少存储，不删除路径或实验文件。备份包含逐文件捕获时刻；原训练保持运行，因此不是所有文件同一瞬间的原子快照。

本分支方便浏览代码；完整原始工作目录和所有中间文件从全量Release恢复。
