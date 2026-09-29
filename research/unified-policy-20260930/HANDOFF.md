# 本轮有界统一策略实验已交付，能力目标未达标（2026-09-29T18:16:41.184823+00:00）

同一策略仍不能稳定覆盖0/1/2+3。最终每来源128初态，2秒严格[127,128,120,2]，5秒[126,128,128,5]；源3body115/128、118/128。G0/G1开发复核通过，统一teacher未过G2，student未触发。两种初始化和两项修正均已停止，不得根据已打开最终集重新选点/调参；本轮不再训练。唯一保留续研起点是历史初始化BC100（最佳失败候选，不是已验证部署策略），路径 `runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth`，SHA `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`。

公开Release https://github.com/Jr-kelly/artgym/releases/tag/wuji-unified-policy-20260930-v1 ，27资产服务器SHA全部通过；2视频和最佳候选归档无认证公网下载SHA通过，候选归档已实际恢复CPU读取BC100/800更新与Adam/RNG。43个checkpoint全部有归档，5120条最终回合双实现复算一致。完整报告README.md、恢复命令REPRODUCE.md、最终交付final-delivery.json、视频video-manifest.json、权重weights-index.json。新分支 `feat/wuji-unified-policy-20260930`，已核验科学结果/Release tag commit `af19615f610517c3da59c3efc285bf169400c09b`；随后提交的交付记录以分支HEAD为准。

活动GPU进程/排队作业/自建监控：无。远端授权主机10.13.160.5:33024于18:07:41UTC再次实查4卡0%/0MiB、无计算，monitor3901不存在；本机最后视频17:45:55UTC结束，随后实查无计算。H200相机两次段错误日志保留，RTX4090固定四开发初态重仿真成功，2/5秒均600帧20秒，四列标同权重teacher与实际成功失败。不是最终统计抽样、不是真机。

总账记录1.9083GPUh，未计时早期CUDA预检保守另留0.25，总预算账2.1583GPUh，最大2卡。整机观测83.2min均23.08%，未覆盖完整4h，不能宣称达到四小时26%门槛。预算起点09-29 15:56:50UTC/截止09-30 07:56:50UTC；按失败规则提前交付，非耗尽预算。

下一轮唯一优先：在新Goal中做实际执行动作/物理目标监督的同起点同预算对照，先定位源3混合BC目标误差；本轮未运行第三修改，不以PPO/student/扩大容量替代证据。所有旧训练、Release和网站保留。

实验副本 `/data/research/artgym-experiments-20260921/unified-policy-20260930`。详情DECISIONS.jsonl和实验根runs/wuji-goal/journal/events.jsonl。原工作区除续接文档外不改；禁止子代理。若需要push：origin是本地备份，真实远端github；helper外部gitconfig权限问题用common.git rsync到/tmp/wuji-unified-publish.git后bare push解决，禁止force。
