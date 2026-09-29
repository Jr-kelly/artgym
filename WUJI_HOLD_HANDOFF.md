<!-- HOLD_CURRENT_START -->
# 当前端点保持实验续接（2026-09-29T07:28:50.732807+00:00）

Goal active；实验副本 `/data/research/artgym-experiments-20260921/hold-20260929`；分支 `feat/wuji-hold-controlled-20260929`；最新已push `ccb7a5e`。禁止子代理。

硬截止2026-09-29 18:08:43UTC，17:08:43起至少留1h冻结评估与交付。四核心训练从CP1000各追加1000轮至CP2000，唯一源内条件GoalDistance2 .1→1.0。稳定奖励日程起终相同；44.4%不是约束未生效，禁止据此延长全组。

远端 `.107:30296`，SSH key `/home/agiuser/.ssh/id_ed25519_h200`，root `/home/wangjiarui/artgym-hold-20260929`，Python `/home/wangjiarui/artgym-runtime/bin/python`。下列PID/轮数仅此时间采样，接手重查：
- hold_r3_original_seed2901: GPU0, PID6454, CP1251, running
- hold_r11_dense1_seed2901: GPU3, PID6460, CP1256, running
- hold_r3_dense1_seed2901: GPU1, PID6455, CP1250, running
- hold_r11_original_seed2901: GPU2, PID6458, CP1257, running

四开发等待器7483–7486、两最终等待器7487/7488已于07:09UTC验证存活，等训练完成；不要重复启动。开发32选CP1250/1500/1750/2000，最终128每源同GPU同扰动主表CP2000。原3抓姿扰动仅条件整合预留。

本地monitor session40377、CP备份58950、完成后全权重归档/上传73336均有界运行。日志在runs/hold-20260929；源11两组CP1250已07:28UTC备份核验，源3即将到点。Release草稿398889931/tag wuji-hold-20260929-v1已7资产，仅父/预检/父视频；未公布新策略结论。

两父策略历史第0回合5秒视频已新渲染，strict均0/1；源3body1/1、源11body0/1；单独本地4090回合非冻结128证据。视频videos/hold-parent-source{3,11}-fixed5.mp4，评分research/hold-20260929/video/。本机渲染已结束。

附件Codex-Goal-Wuji-Hold-20260929.md仍未找到、路径问题待回复；仅依据明确用户指令执行，不声称已读。

下一步：完成四组CP1250备份并保持同预算训练；冻结最终结果后按preregistration判据再决定种子复验/整合。需要运行analyze_wuji_hold与plot_wuji_hold_results、补最终策略固定回合视频、归档所有raw trace、完成报告/交接并commit/push/publish。不得把本次中期快照当完成。
<!-- HOLD_CURRENT_END -->

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

## 2026-09-29T06:45:02.042996+00:00 core_configuration_and_source_pin_verified

实查四正式训练命令：每源两条件除实验名外仅GoalDistance2权重.1→1.0不同；模型/优化器/学习率起点摘要成对相同。已保存远端运行源码逐文件SHA，训练源码保持不变。
证据：research/hold-20260929/receipts/core-source-config-audit.json, research/hold-20260929/receipts/core-row3-identity.json, research/hold-20260929/receipts/core-row11-identity.json。下一步：继续同预算训练，保存里程碑；冻结评估入口和独立复算已准备。

## 2026-09-29T06:46:08.067739+00:00 endpoint_diagnostic_label_corrected

离线端点标签初版误用绝对slider>0.02判断伸出，已保留invalid文件并按冻结命令阶段偶数伸出/奇数收回修正。任务目标是init_slider+.04和init_slider，不是全局.04/0。原始物理/误差/严格评分及训练配置不受影响。
证据：research/hold-20260929/diagnosis/by-endpoint.json, research/hold-20260929/diagnosis/by-endpoint.invalid-absolute-threshold.json。下一步：用正确阶段标签解释到达后回缩/过冲，继续既定单系数对照。

## 2026-09-29T06:50:07.139309+00:00 hold_initial_snapshot_pushed

新分支feat/wuji-hold-controlled-20260929首个实验快照fa49855已push；奖励日程纠正、既有时序诊断、冻结方案/数据、可运行续训/评估入口已保存。正式四训练保持运行，不当成完成。
证据：research/hold-20260929/state.json, research/hold-20260929/README.md。下一步：按实测吞吐继续核心训练，完整冻结评估后才决定追加复验/整合。

## 2026-09-29T06:52:03.013021+00:00 resolved_hold_configs_verified

从实际训练命令解析四份完整Hydra配置，逐键核对通过：源内唯一实质差异为GoalDistance2 .1→1.0；span、绝对位姿惩罚、奖励起终值、物理与网络均相同。已存完整YAML和SHA。
证据：research/hold-20260929/configs/audit.json。下一步：保持核心训练预算，待冻结结果再判定额外奖励是否改善端点保持。

## 2026-09-29T06:52:48.371938+00:00 followup_decision_rules_recorded_before_outcomes

在任何新策略评估前补充后续判据：改动相对原续训在某源严格2/5均值至少+10个百分点且刀身稳定不下降>5点，才优先该源成对续训种子复验；专家均值≥50%且优于父策略才视预算尝试原3+有效新增源的单策略整合。源11若仍失败明确不声称已整合。完整同预算结果始终报告，不按有利协议隐藏退化。
证据：research/hold-20260929/preregistration.json。下一步：按既定训练/冻结结果判据选择后续，禁止提前认定奖励有效。

## 2026-09-29T06:56:39.526895+00:00 archive_restore_flow_verified

已用完成的10轮源3原奖励预检实际验证全权重/日志归档和恢复：9文件远端本地SHA一致，179714847字节包恢复核验通过。预检权重不参与正式对照或选点。附件在/home/agiuser及/mnt再次按完整文件名搜索仍未找到，按明确用户指令继续。
证据：research/hold-20260929/receipts/archive-restore-preflight-check.txt, research/hold-20260929/receipts/preflight_r3_original-archive.json。下一步：保持核心四臂运行，完成后使用相同归档流程保存所有权重与日志。

## 2026-09-29T06:58:30.682717+00:00 hold_delivery_draft_created

本轮Release草稿id398889931/tag wuji-hold-20260929-v1已建立，仅用于保存不可变证据，正式结论尚未发布。父专家权重与预检归档上传中；核心四训练继续，最终必须待冻结结果完成再发布。
证据：research/hold-20260929/receipts/release-created.json, research/hold-20260929/receipts/parent-weights.json。下一步：保存全部权重/时序与配置，完成核心冻结表后决定追加实验。

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

## 2026-09-29T07:28:00.291398+00:00 checkpoint_backed_up

hold_r11_original_seed2901:1250 remote/local SHA and CPU integrity passed; 57c0b77c508c01fa4f5a783473d1a42bd46b4948d1ec40165fff5b5385a49bc7
证据：research/hold-20260929/receipts/backup-core.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T07:28:04.210817+00:00 checkpoint_backed_up

hold_r11_dense1_seed2901:1250 remote/local SHA and CPU integrity passed; d1f4ab58cdfd9f1d683a1d6a9b28994527556b325c57b7eaeb88e5343b3400be
证据：research/hold-20260929/receipts/backup-core.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T07:28:56.092643+00:00 checkpoint_backed_up

hold_r3_original_seed2901:1250 remote/local SHA and CPU integrity passed; 8c79ff6a2593402d07b08f3474255adafd96d21cdb32fed9d22c00220a19e4d3
证据：research/hold-20260929/receipts/backup-core.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T07:28:59.977592+00:00 checkpoint_backed_up

hold_r3_dense1_seed2901:1250 remote/local SHA and CPU integrity passed; 694433b62b851caf8494d3766917343af72b5848357e7025d919121f26aaec44
证据：research/hold-20260929/receipts/backup-core.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T07:34:54.393303+00:00 frozen_evidence_collector_started

本地冻结证据收集器session22003等待两源最终结果，完成后镜像开发/最终全部原始时序、逐文件远端/本地SHA核验、归档并运行独立严格复算与逐端点诊断；不新增物理或改变远端训练/评估。
证据：research/hold-20260929/receipts/collector-start.json。下一步：保持核心训练，检查各有界队列错误日志，最终表完成后按冻结判据决策。
