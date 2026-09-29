# 本轮统一策略：计算与验证结束，正在发布（2026-09-29T18:03:31.544908+00:00）

唯一保留的统一续研起点：`runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth`，SHA `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`。它是最佳失败候选，不是已验证部署策略。最终128逐来源严格2秒[127,128,120,2]、5秒[126,128,128,5]；源3body115/118。teacher未过G2，student未触发。完整报告README.md、恢复命令REPRODUCE.md、最终冻结final-freeze.json、权重weights-index.json、视频video-manifest.json。

所有训练按两初始化与两修正的失败停止规则结束，不得继续第三方法或根据最终集调参。后续只优先在新一轮检验实际执行动作/物理目标监督的同预算对照；本轮不再训练。原生Goal待公开发布、下载核验和远端commit核验完成后结束。

活动GPU进程：无。远端授权H200主机10.13.160.5:33024于17:41:37UTC实查4卡0%0MiB、无计算进程，自建monitor3901终止且PID消失；本机最后视频于17:45:55UTC完成，17:56UTC实查无计算进程。H200相机初始化两次-11失败日志保留，RTX4090两协议视频成功，600帧20s并四列预览已检查。新Release `wuji-unified-policy-20260930-v1` 的最后CPU上传/验证进行中；没有无人看护GPU队列。

记录1.9083GPUh，早期未计时预检保守另计0.25，总账2.1583/max24；最大2卡。整机观测83.2min均23.08%，未有完整4h统计，不宣称利用率达标。开始09-29 15:56:50UTC，截止09-30 07:56:50UTC，按规则提前收尾。

分支feat/wuji-unified-policy-20260930，最新GitHub已核验28d853f，后续最终报告还要commit/push。真实远端github；本地origin是备份。直接push helper外部gitconfig会EPERM，使用common.git到/tmp/wuji-unified-publish.git的rsync(bare,排除worktrees/index/logs)后push，禁止force。最终发布target应为本轮最终科学结果commit；下载核验收尾记录允许后续commit，不能改已有历史tag/release。

所有数据在独立worktree `/data/research/artgym-experiments-20260921/unified-policy-20260930`；大文件delivery/unified-policy-20260930只上传独立Release，不进Git。完整阶段记录DECISIONS.jsonl以及实验根runs/wuji-goal/journal/events.jsonl。原工作目录训练和用户修改保持。
