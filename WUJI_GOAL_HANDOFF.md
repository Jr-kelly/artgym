# Wuji端点保持受控实验续接

本轮起点2026-09-29 06:08:43UTC，硬截止18:08:43，17:08:43前停止新增训练并留至少1小时冻结评估与交付。独立分支feat/wuji-hold-controlled-20260929，源f332e4e；本目录为新实验，历史multigrasp副本完整保留。禁止子代理。

明确纠正上一轮建议：ObjPosDeviation、ObjRotDeviation、StableContact的curriculum起止分别都为-.5/-.02/0，absolutePoseObjective coefficient1/ramp0。44.4%仅日程记录，不代表约束未生效；不得据此直接延长全部训练。本轮从相同源3/11专家最终checkpoint做原奖励续训与一个最小保持改动同预算比较；先读实际失败时序。

新主机10.14.0.107:30296在06:12UTC实测4H100全部空闲、无计算PID，旧runtime和multigrasp文件存在；需随时重查。首次host key未登记连接失败，accept-new登记后成功，无凭据改动。附件Codex-Goal-Wuji-Hold-20260929.md暂未在下载/tmp/research找到，已请求路径，继续明确授权的独立工作。下一步：离线时序诊断、运行时与权重核验、冻结最小比较方案和吞吐预检。

## 2026-09-29T06:38:15.402936+00:00 paired_resume_preflight_started

源3/11×原奖励/已有GoalDistance2系数1.0四臂各10轮恢复预检已06:37UTC启动，远端launchPID5604/5605/5606/5607，GPU0/1/2/3。完全相同父checkpoint，保持物理网络span.04和原成功阈值。恢复模型/优化器/内在奖励状态/计数器，PhysX未序列化所以成对重置rollout和RNN。
证据：research/hold-20260929/receipts/preflight-launch.json, research/hold-20260929/preregistration.json, research/hold-20260929/diagnosis/report.json。下一步：验证预检实际进程和恢复摘要，按实测吞吐锁定正式相同追加步数。

## 2026-09-29T06:39:15.526249+00:00 remote_transition

preflight_r11_dense1 running observed; PID 5613
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:39:15.526390+00:00 remote_transition

preflight_r11_original running observed; PID 5615
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:39:15.526458+00:00 remote_transition

preflight_r3_original running observed; PID 5612
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:39:15.526518+00:00 remote_transition

preflight_r3_dense1 running observed; PID 5618
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:18.528737+00:00 remote_transition

preflight_r11_dense1 completed observed; PID 5613
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:19.646111+00:00 remote_transition

preflight_r11_original completed observed; PID 5615
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:19.646675+00:00 remote_transition

hold_r3_original_seed2901 running observed; PID 6454
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:19.647021+00:00 remote_transition

hold_r11_dense1_seed2901 running observed; PID 6460
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:20.663487+00:00 remote_transition

preflight_r3_original completed observed; PID 5612
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:23.083514+00:00 remote_transition

preflight_r3_dense1 completed observed; PID 5618
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:23.083788+00:00 remote_transition

hold_r3_dense1_seed2901 running observed; PID 6455
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:23.083899+00:00 remote_transition

hold_r11_original_seed2901 running observed; PID 6458
证据：research/hold-20260929/receipts/monitor-latest.json。下一步：Verify full evidence and preserve matched-budget comparison。

## 2026-09-29T06:40:54.154904+00:00 core_equal_budget_training_started

四个10轮预检全部成功，成对模型/优化器/学习率/计数器恢复摘要相同，实测10.7–10.9秒每轮。正式四臂从原专家CP1000各追加1000轮至CP2000，163840000新增交互；唯一因子为已有GoalDistance2 .1或1.0，固定其它所有物理/动作/网络/严格指标。5h看护上限，预计约3h完成，预留末1h交付。
证据：research/hold-20260929/receipts/core-launch.json, research/hold-20260929/receipts/preflight-resume-verified.json, research/hold-20260929/preregistration.json。下一步：核验正式运行配置与恢复摘要，准备预冻结开发/独立扰动及同GPU最终评估。

## 2026-09-29T06:43:00.079167+00:00 hold_evaluation_queues_frozen

开发每源32独立扰动、最终每源128扰动在新策略评估前冻结；4候选CP1250/1500/1750/2000开发严格2/5平均选点，主表固定CP2000同预算。已启动四开发等待器和两最终等待器，等待截止16:00UTC；最终每源两臂/父专家在同GPU同128初態评估，原3抓姿仅为条件整合预留。
证据：research/hold-20260929/data/manifest.json, research/hold-20260929/receipts/evaluation-queues.json, scripts/evaluate_wuji_hold.py。下一步：训练持续、核验配置与哈希并保存中期权重；不查看最终结果选择checkpoint。

旧实验完整历史见相邻multigrasp-20260928副本；共享最新版在/data/research/artgym/WUJI_GOAL_HANDOFF.md。

## 2026-09-29T07:03:38.875647+00:00 offline_diagnostic_reproduction_passed

通用逐阶段保持诊断在既有896阶段上全部复现；按命令奇偶标伸出/收回，新增冻结复算将输出同口径端点表。父专家与预检Release资产服务器SHA核验通过。资源统计明确区分实际采样覆盖和四小时门槛，不将短时均值冒充四小时。
证据：research/hold-20260929/receipts/stage-diagnostic-reproduction.json, research/hold-20260929/receipts/release-parent-preflight.json, research/hold-20260929/receipts/resources-current.json。下一步：继续四核心同预算训练与权重备份，待最终物理结果后判定后续。

## 2026-09-29T07:08:13.504563+00:00 historical_parent_video_started

本机4090实查仅ToDesk图形会话、无其它训练，开始两源父专家历史诊断集第0回合5秒命令视频；事前固定同回合用于父/原续训/改动对比。视频为单独渲染物理回合，不替代冻结128主表，不选最佳。四H100核心训练保持原样。
证据：research/hold-20260929/video/plan.json。下一步：检查真实渲染结果并留存父策略失败，核心训练继续。

## 2026-09-29T07:11:43.148056+00:00 historical_parent_videos_completed

两源父策略历史诊断第0回合5秒视频完成并检查0/149/299/449/599帧。源3严格0/1、刀身稳定1/1；源11严格0/1、刀身稳定0/1；两者所有命令都曾到位。不得将该单独渲染的源11失败归为纯保持失败，冻结128结果另报。打包首次缺videos目录已补建，未重跑或覆盖历史。
证据：research/hold-20260929/video/parent-video-results.json, research/hold-20260929/video/parent-source3-contact-sheet.png, research/hold-20260929/video/parent-source11-contact-sheet.png。下一步：核心训练继续，最终策略完成后使用同历史回合补对比视频；当前本机物理已结束。

## 2026-09-29T07:19:11.828376+00:00 core_archive_queue_started

本地有界归档等待器已启动，四核心训练完成后逐组保存全部权重/日志并上传Release草稿核验SHA；不修改远端训练，16:30UTC截止。当前草稿7资产均为父权重/预检/父视频，尚无正式新策略结论。
证据：research/hold-20260929/receipts/archive-queue-start.json, research/hold-20260929/state.json。下一步：核验首批CP1250，继续固定预算与冻结评估队列。
