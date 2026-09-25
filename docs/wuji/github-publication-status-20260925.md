# GitHub 发布覆盖核验 · 2026-09-25

结论：核心 teacher + student 交付完整、历史实验已有大量发布，但不能说所有进展/尝试和工作目录都已完整同步到 GitHub。本轮是状态审计，没有上传或修改远端内容。

## 在线核验

仓库 `Jr-kelly/artgym`，按 Release assets 分页接口实查（不能只依赖列表接口内嵌 assets，它对第一个 Release 少显示1项）：

|Release|实际资产数量|内容|
|---|---:|---|
|[wuji-knife-demo-v1.0.0](https://github.com/Jr-kelly/artgym/releases/tag/wuji-knife-demo-v1.0.0)|3|早期无字脚本 demo|
|[wuji-visualizations-20260921](https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921)|1000|资产/初态可视化、早期训练和失败分析、代码与证据包等|
|[wuji-experiments-20260923](https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923)|327|后续实验、配对/多seed及最终 teacher + student|

合计1330个 Release 资产，不等于1330项实验或所有原始文件。最后资产上传完成于2026-09-24 06:51:58 CST。

最终核心包17/17文件已用当前本机 SHA256 对本轮 GitHub asset digest 重新核验，全部一致：teacher、student、源码tar.gz及manifest、新300初态、评估JSON、证据ZIP、README、哈希表、四个无字视频与四张抽帧图。

本机 `runs/wuji-goal/release-*` 中66个发布目录，65个目录的所有顶层文件均可按名字与大小匹配 GitHub。余下一目录仅 `plot-provenance.json` 无同名独立资产；未因此直接认定内容漏传，因为可能已改名或包含于别的包。此范围只覆盖已整理发布目录，不覆盖工作目录所有实验文件；除核心包外，本轮未重新校验全体大文件哈希。

GitHub 分支实查只有：

- `main`：`63b94fb3364596db51b7e4651b3c3c98ff994710`，上游版本。
- `demo/wuji-knife-fingertip`：`313ba8ea22113db52be3350e59b88050d03326ec`，2026-09-20早期demo。

因此后续实验源码虽已作为Release压缩包上传，但尚未形成普通Git分支里的最新可浏览代码；直接clone上述分支不会得到完整的最终实验代码。

## 确认尚未更新到 GitHub 的部分

1. 2026-09-24 15:20以后形成的 sim2real 论文核验与建议文档、原文摘录回执。
2. 最近的本地视频服务修复、sim2real讨论等最新接续文档/事件日志版本，均晚于最后Release上传。
3. 将最终实验源码整理成最新Git分支，以及一份将所有实验尝试与对应Release资产串起来的统一索引。
4. 所有原始日志、所有中间CP、所有远端文件尚无逐文件全量同步证明。不能把发布证据包等同整个工作目录备份；本轮没有重新连接训练机器盘点。

用户此前澄清后的后续路线应为：先保留尺寸/滑块位置/行程接近实物的简化模型，优先真实标定与DR；根据实机失败再按需细化局部几何。精细CAD不是部署前必须先做的前置项，若真实刀需要按压解锁则另须补机构。

## 机器可读证据

- `runs/wuji-goal/diagnostics/github-publication-audit-20260925-v1/all-assets.json`
- 同目录 `release-<id>-assets.json`：三个Release完整分页列表。
- 同目录 `report.json`：核心哈希校验、66个目录匹配及限制。

核心teacher SHA256：`4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。
核心student SHA256：`022ad8c7b3af18e25681fcd4073c1b48858621470293036df0311c488068e0f5`。
