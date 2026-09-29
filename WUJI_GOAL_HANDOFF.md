<!-- HOLD_CURRENT_START -->
# 当前端点保持Goal：本轮有界实验与GitHub交付完成，行为目标部分达成

截至2026-09-29T14:27:32.202255+00:00。工作区`/data/research/artgym-experiments-20260921/hold-20260929`，分支`feat/wuji-hold-controlled-20260929`，实验结果55bccd0、发布核验3c2a0e9均已push并由GitHub API核验；本次只收尾交接状态。禁止子代理。原12h预算06:08:43—18:08:43UTC，全部计算14:22UTC前结束；14:23UTC开发机4H100均0%、1MiB、无计算PID，已告知用户释放。14:25UTC仅自建本地monitor1521593核验身份后停止，其它任务未碰。**不要重启任何旧实验或等待器。**

核心同预算每臂+1000epoch/163840000交互：源3原57/128、65/128，改动109/128、120/128；均值47.65625%→89.453125%。第二续训种子源3原27/128、36/128，改115/128、123/128；24.609375%→92.96875%。两种子仅续训RNG不同，父专家和测试集相同。源11原0/0、改1/1（各128），仍未解决。源3改动为已有GoalDistance2系数.1→1，物理/网络/动作范围/严格成功固定。奖励日程起终相同，44.4%不是稳定约束未生效。

共享整合：同源3改动CP2000父，singleton3 vs shared0/1/2/3各+1000epoch至固定CP3000。共享原0/1/2严格全部0/128，源3为118/128、124/128；同表单源109/122、父112/117。历史策略原0/1/2为126/124、127/128、126/127（各128），全部旧成功权重保留。整合未通过每源每协议>=50%门槛。父本来不具备原抓姿技能，不能称本次共享训练遗忘父的已有原技能。原抓姿共享刀身通常<1s失稳；同批静态/历史策略大多稳定，仅描述，未证明统一根因。

源11机制：脚本到位后固定拇指目标使严格2/5从1/1变36/59，但body125/122变92/87（各128），不是学习策略成功。下一步唯一优先事项：源11到位后拇指保持与非拇指支撑协同的受控修复，端点和刀身同时约束；不直接采用脚本固定，不追加本轮训练。

所有冻结时序本地/远端SHA和独立端点评分交叉复算通过：analysis-seed2901、analysis-seed2902、analysis-integration、analysis-thumb-latch，汇总followup-summary。实际核心/复验/整合开发与最终物理12800回合，额外干预512、视频14；复用结果不重复算物理独立回合。均仿真已训练基础抓姿邻域，非未见抓姿/真机。

32正式CP全部SHA/CPU核验，8完整训练归档恢复核验，30Release资产服务器SHA核验。Release id398889931/tagwuji-hold-20260929-v1，已正式发布 https://github.com/Jr-kelly/artgym/releases/tag/wuji-hold-20260929-v1 ，30资产服务器SHA全部核验；8段公开视频下载SHA全部通过；发布记录已提交，无待执行任务。所有8视频已上传且检查；video/integration-inspection.json等。代表源3dense1视频严格1/1；源11dense1为0/1；整合两段均仅源3成功1/4。

训练归档等待器旧session49802读心跳空JSON退出，保留archive-followup.log，修复有界重试后v2session69676成功完成4归档；没有训练重启。视频打包改用现成imageio_ffmpeg，既有文件SHA一致后续接。所有train/eval/backup/collect/archive/render会话已完成；monitor已停，无待跑队列。

详细报告`research/hold-20260929/README.md`；`weights-index.json`；资源`receipts/resources-final.json`，训练含预检26.2475GPUh，结束前4h整机利用率77.465%/100%覆盖；释放凭据`receipts/remote-released.json`。附件Hold文档未在可见路径找到，依明确用户消息执行，不声称已读。
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

## 2026-09-29T07:34:54.393303+00:00 frozen_evidence_collector_started

本地冻结证据收集器session22003等待两源最终结果，完成后镜像开发/最终全部原始时序、逐文件远端/本地SHA核验、归档并运行独立严格复算与逐端点诊断；不新增物理或改变远端训练/评估。
证据：research/hold-20260929/receipts/collector-start.json。下一步：保持核心训练，检查各有界队列错误日志，最终表完成后按冻结判据决策。

## 2026-09-29T08:19:00.333423+00:00 core_midbudget_verified

四核心训练CP1250/1500共8个checkpoint全部远端/本地SHA、epoch/frame、模型有限性和优化器存在检查通过；各组新增预算已过半，仍固定CP2000结束。无新冻结结果，不依据训练奖励判定改善。
证据：research/hold-20260929/receipts/backup-core.json。下一步：继续至CP1750/2000；开发与最终等待器保持原样，后续按最终严格结果决策。

## 2026-09-29T08:21:29.829279+00:00 user_resource_release_estimate

用户要求继续并询问释放开发机时间。08:21UTC实測四组剩85–91分钟，预计09:45–09:52UTC训完，核心冻结评估预计再20–40分钟；对用户给北京时间18:15–18:35左右可释放核心占用的估计。后续若证据支持复验/整合，启动前明确额外占用，不默认偷偷延长。
证据：research/hold-20260929/receipts/resource-release-estimate.json。下一步：继续固定核心预算，按实测评估吞吐更新释放估计。

## 2026-09-29T08:23:59.325530+00:00 frozen_state_reproduction_verified

10份冻结初态从记录种子逐位重现通过，未覆盖数据。每个源内开发/最终种子不同；跨源dev11与final1共享随机种子但基础抓姿不同，明确不声称所有跨源随机扰动相互独立。
证据：research/hold-20260929/receipts/frozen-states-reproduced.json。下一步：继续核心训练；最终评估解释限定已训练基础抓姿附近扰动。

## 2026-09-29T08:45:56.354358+00:00 final_video_queue_started

四最终策略固定历史第0回合视频等待器session33434已启动，等待全部CP2000备份后本机4090空闲才渲染；不额外占用开发机远端GPU，结果保留真实成功/失败。
证据：research/hold-20260929/receipts/final-render-queue.json, research/hold-20260929/video/plan.json。下一步：继续核心训练，最终冻结评估与本机视频可并行，按实际进度更新释放时间。

## 2026-09-29T09:09:33.134106+00:00 core_three_quarter_budget_verified

四组CP1250/1500/1750共12正式权重全部本地/远端SHA、CPU轮数/交互计数/有限性/优化器检查通过；训练剩最后250轮，开发/最终等待器不变。
证据：research/hold-20260929/receipts/backup-core.json, research/hold-20260929/state.json。下一步：完成最终CP2000，核查开发评估接续与实际耗时，更新GPU释放时间。

## 2026-09-29T09:50:50.207025+00:00 completed_training_archive_started

hold_r11_original_seed2901 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T09:52:18.174478+00:00 completed_training_archive_uploaded

hold_r11_original_seed2901 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r11_original_seed2901.json, research/hold-20260929/receipts/hold_r11_original_seed2901-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T09:52:18.174820+00:00 completed_training_archive_started

hold_r11_dense1_seed2901 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T09:54:38.325088+00:00 completed_training_archive_uploaded

hold_r11_dense1_seed2901 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r11_dense1_seed2901.json, research/hold-20260929/receipts/hold_r11_dense1_seed2901-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T09:56:41.492955+00:00 completed_training_archive_started

hold_r3_original_seed2901 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T09:57:35.819817+00:00 final_representative_video_started

video-final-r3-original-fixed5: fixed historical trial0; separate local4090 evaluation, not frozen128 quantitative evidence
证据：research/hold-20260929/video/plan.json, research/hold-20260929/receipts/backup-core.json。下一步：Render actual learned policy and retain true outcome。

## 2026-09-29T09:58:04.959932+00:00 all_core_training_completed

四组核心训练均正常退出CP2000，每组从同源CP1000追加163840000交互；四保存点共16权重全部远端/本地SHA和CPU完整性核验通过。开发评估已接续，本机最终视频队列等待备份完成后启动。训练完成不等于行为改善。
证据：research/hold-20260929/receipts/core-training-complete.json, research/hold-20260929/receipts/backup-core.json。下一步：完成冻结评估与独立时序复算，按预注册判据决定后续。

## 2026-09-29T09:58:28.257303+00:00 completed_training_archive_uploaded

hold_r3_original_seed2901 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r3_original_seed2901.json, research/hold-20260929/receipts/hold_r3_original_seed2901-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T09:58:28.257520+00:00 completed_training_archive_started

hold_r3_dense1_seed2901 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T09:58:42.018532+00:00 final_representative_video_completed

video-final-r3-original-fixed5: actual strict 0/1
证据：runs/hold-20260929/video-final-r3-original-fixed5/evidence/report.json。下一步：Inspect fixed frame contact sheets, archive raw trace and video。

## 2026-09-29T09:58:42.089667+00:00 final_representative_video_started

video-final-r3-dense1-fixed5: fixed historical trial0; separate local4090 evaluation, not frozen128 quantitative evidence
证据：research/hold-20260929/video/plan.json, research/hold-20260929/receipts/backup-core.json。下一步：Render actual learned policy and retain true outcome。

## 2026-09-29T09:59:48.262109+00:00 final_representative_video_completed

video-final-r3-dense1-fixed5: actual strict 1/1
证据：runs/hold-20260929/video-final-r3-dense1-fixed5/evidence/report.json。下一步：Inspect fixed frame contact sheets, archive raw trace and video。

## 2026-09-29T09:59:48.323052+00:00 final_representative_video_started

video-final-r11-original-fixed5: fixed historical trial0; separate local4090 evaluation, not frozen128 quantitative evidence
证据：research/hold-20260929/video/plan.json, research/hold-20260929/receipts/backup-core.json。下一步：Render actual learned policy and retain true outcome。

## 2026-09-29T10:00:04.726735+00:00 completed_training_archive_uploaded

hold_r3_dense1_seed2901 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r3_dense1_seed2901.json, research/hold-20260929/receipts/hold_r3_dense1_seed2901-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T10:00:57.492650+00:00 final_representative_video_completed

video-final-r11-original-fixed5: actual strict 0/1
证据：runs/hold-20260929/video-final-r11-original-fixed5/evidence/report.json。下一步：Inspect fixed frame contact sheets, archive raw trace and video。

## 2026-09-29T10:00:57.554759+00:00 final_representative_video_started

video-final-r11-dense1-fixed5: fixed historical trial0; separate local4090 evaluation, not frozen128 quantitative evidence
证据：research/hold-20260929/video/plan.json, research/hold-20260929/receipts/backup-core.json。下一步：Render actual learned policy and retain true outcome。

## 2026-09-29T10:02:06.846237+00:00 final_representative_video_completed

video-final-r11-dense1-fixed5: actual strict 0/1
证据：runs/hold-20260929/video-final-r11-dense1-fixed5/evidence/report.json。下一步：Inspect fixed frame contact sheets, archive raw trace and video。

## 2026-09-29T10:10:45.364605+00:00 all_development_frozen_two_gpus_free

32项开发评估全部完成并冻结：源3原CP2000均值45.3125%、改动CP1500选点96.875%(其CP2000为84.375%)；源11原0、改动1.5625%，均选CP2000。10:09UTC实查GPU1/3无计算PID、0%/1MiB；GPU0/2继续同卡最终128评估。开发信号不替代最终结论。
证据：research/hold-20260929/receipts/development-frozen-all.json。下一步：完成最终128主表和独立复算；若触发后续先向用户说明新增占用。

## 2026-09-29T10:19:18.515162+00:00 core_frozen_evidence_collected

Source11 seed2901: development and final raw evidence mirrored; every remote/local file SHA verified
证据：research/hold-20260929/receipts/raw-row11-seed2901.json。下一步：Independently rescore both sources before followup decisions。

## 2026-09-29T10:28:41.944494+00:00 core_frozen_evidence_collected

Source3 seed2901: development and final raw evidence mirrored; every remote/local file SHA verified
证据：research/hold-20260929/receipts/raw-row3-seed2901.json。下一步：Independently rescore both sources before followup decisions。

## 2026-09-29T10:28:53.185169+00:00 core_frozen_independent_rescore_completed

seed2901 both sources independently rescored; matched-budget and selected results remain separate
证据：research/hold-20260929/analysis-seed2901/report.json。下一步：Inspect all counts and endpoint diagnostics; apply frozen followup criteria。

## 2026-09-29T10:31:13.469563+00:00 followup_budget_and_pools_frozen

核心独立复算源3改动均值89.453125% vs原47.65625%(+41.796875pp)，body仅-0.78125pp，触发复验与整合。冻结第二续训seed2902源3两臂各1000新增轮；整合seed2903同改动CP2000起点单源vs原3+源3各1000轮至3000，仅池不同。源11排除。已向用户说明预计额外四卡3.5h训练+约.5h评估、北京时间22:15–22:45释放。
证据：research/hold-20260929/followup-decision.json, research/hold-20260929/integration-plan.json, research/hold-20260929/replication-plan.json。下一步：同步新增入口/冻结配置，核查GPU空闲后启动4个有用后续任务，保持17:08UTC预留。

## 2026-09-29T10:34:38.432661+00:00 followup_running_identity_verified

后续4任务已实际更新至复验CP1006/整合CP2006，PID114963/114961/114965/114967。源3复验模型/优化器/学习率起点成对完全相同；整合两臂亦同CP2000模型/优化器/学习率，仅训练池不同。动作/物理/网络不变。复验评估等待115408–115410，整合115411；备份本地4989/9624、全归档49802已启动。
证据：research/hold-20260929/receipts/followup-launch.json, research/hold-20260929/receipts/followup-pair-audit.json, research/hold-20260929/receipts/followup-evaluation-queues.json。下一步：保持1000轮同预算，核验后续完整Hydra配置并收集最终物理结果，停止新增任务留交付余量。

## 2026-09-29T10:39:19.907198+00:00 followup_resolved_configs_verified

后续4份完整Hydra配置解析并逐键比较通过：复验仅奖励系数，整合仅训练池，除实验标识外无其它差异。本地只读解析首次IsaacGym导入SIGSEGV，改远端后发现缺少离线flatten模块，补同步该辅助模块后通过；均未改训练源码/进程。
证据：research/hold-20260929/configs-followup/audit.json, research/hold-20260929/receipts/followup-config-audit.log。下一步：继续固定预算后续训练，整理核心报告和全部权重/原始时序交付。

## 2026-09-29T10:42:30.085997+00:00 source11_thumb_latch_diagnostic_started

源11核心无改善，冻结本机4090机制对照：同CP2000系数1、同128初态、同GPU，各2/5秒比较原策略与到位连续9步后令拇指增量0至换向。只诊断持续拇指指令是否参与破坏保持，不当成学习策略/部署成功；不改核心结果，不占远端后续4GPU。
证据：research/hold-20260929/thumb-latch-plan.json, scripts/audit_wuji_hold_thumb_latch.py。下一步：运行4个有界物理诊断、独立复算并区分脚本干预与原策略结果。

## 2026-09-29T10:49:50.096111+00:00 source11_thumb_latch_diagnostic_completed

本机源11机制对照512回合完成，独立逐步核验9步触发/换向复位/只改拇指及严格评分通过。原策略2/5严格1/1（各128），固定拇指目标36/59；刀身稳定125/122降至92/87。说明持续拇指增量参与保持破坏，但简单冻结有稳定性代价，不能当学会保持或直接修复。全部原始trace/动作干预归档，本机物理结束，远端4后续训练继续。
证据：research/hold-20260929/analysis-thumb-latch/report.json, research/hold-20260929/receipts/thumb-latch-raw-manifest.json。下一步：完成既定种子复验和共享策略整合，不扩散附加训练；报告机制限制。

## 2026-09-29T10:59:25.435702+00:00 integration_video_queue_frozen

在整合结果出现前固定singleton/shared最终CP3000四源视频回合0/128/256/384（各来源第0扰动），5秒协议，本机4090无其它计算时才渲染；等待器session29611，不占远端GPU。
证据：research/hold-20260929/integration-video-plan.json, research/hold-20260929/receipts/followup-local-queues.json。下一步：继续四后续同预算训练及里程碑备份，完成冻结评估和可审查交付。

## 2026-09-29T11:20:35.250239+00:00 checkpoint_backed_up

hold_integrate_singleton_seed2903:2250 remote/local SHA and CPU integrity passed; df9e0353d429b443943130cef89d70530c86258d55c6dcf305b18d1ca0a2fa4a
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T11:20:35.948974+00:00 checkpoint_backed_up

hold_r3_dense1_seed2902:1250 remote/local SHA and CPU integrity passed; 285bdf66f25f7e9133fb41bc9d826858f1c171446f956469c8fdd4d0c2e80fd5
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T11:21:25.701398+00:00 checkpoint_backed_up

hold_r3_original_seed2902:1250 remote/local SHA and CPU integrity passed; b2d91f2087ccc74a7973494e17136722d00fa8cff3911101035994e8efe3b00f
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T11:23:42.900859+00:00 checkpoint_backed_up

hold_integrate_shared_seed2903:2250 remote/local SHA and CPU integrity passed; 8150c816cd57cafb83ac6e1af1f48a06ff315b73f08a24df0fca689b6dab5888
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T11:25:29.487526+00:00 followup_first_quarter_checkpoints_verified

后续复验两组CP1250、整合两组CP2250全部远端/本地SHA、CPU轮数/交互/有限性/优化器核验通过，仍固定各新增1000轮终点。源11脚本机制诊断已完整交付，无附加训练。
证据：research/hold-20260929/receipts/backup-replication.json, research/hold-20260929/receipts/backup-integration.json。下一步：继续到复验CP1500/整合CP2500，再完成最终冻结评估和交付。

## 2026-09-29T12:09:04.485610+00:00 checkpoint_backed_up

hold_integrate_singleton_seed2903:2500 remote/local SHA and CPU integrity passed; 9359cf3c9745d37f20bced5920514670c5ba83fd4bc190f549f9b9e7a2a9f3f4
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T12:09:46.033545+00:00 checkpoint_backed_up

hold_r3_dense1_seed2902:1500 remote/local SHA and CPU integrity passed; 2376d96455f811d67d9e3c7f5d75e6ee7b24befd17d0bc2c08c35a372603c87a
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T12:10:35.948193+00:00 checkpoint_backed_up

hold_r3_original_seed2902:1500 remote/local SHA and CPU integrity passed; b299130a2898c6b61c93d41f71e86546357e57aae1994a79c30d18f66ec0435c
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T12:14:30.812360+00:00 checkpoint_backed_up

hold_integrate_shared_seed2903:2500 remote/local SHA and CPU integrity passed; 0170f41adce2cbc9c182d0f602688000789464f544dbb6882c132d0885d8e51a
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T12:15:43.670073+00:00 followup_midbudget_verified

后续复验CP1250/1500及整合CP2250/2500共8权重均SHA和CPU完整性核验通过，四任务已过新增预算半程。固定终点复验2000/整合3000，等待器/采集器保持运行。
证据：research/hold-20260929/receipts/backup-replication.json, research/hold-20260929/receipts/backup-integration.json。下一步：完成后半程训练、冻结评估和视频，最终只报告实测整合结果。

## 2026-09-29T12:58:25.044448+00:00 checkpoint_backed_up

hold_integrate_singleton_seed2903:2750 remote/local SHA and CPU integrity passed; d7092f38ca7e39b2174d6e533163e6ef501ba595b9fcd939a6ba37d7c73ecdcb
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T12:59:52.812801+00:00 checkpoint_backed_up

hold_r3_original_seed2902:1750 remote/local SHA and CPU integrity passed; 953fdadb3803a220d4d1833883e0b72a2ec591fa5ca9984666f5ae69269f3755
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:00:01.786376+00:00 checkpoint_backed_up

hold_r3_dense1_seed2902:1750 remote/local SHA and CPU integrity passed; 0ad136492e49ecf104af0e2a5f25f1c0eb38ceb9d50cf421a9ec02018d94557e
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:04:43.901655+00:00 checkpoint_backed_up

hold_integrate_shared_seed2903:2750 remote/local SHA and CPU integrity passed; c9cc71115b2a60faa276a917ea147aa2dd6b5e8ddc8d7acbc946ebb523a8190e
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:09:04.253030+00:00 followup_three_quarter_checkpoints_verified

后续复验三保存点及整合三保存点共12权重全部SHA/CPU完整性核验通过；13:07UTC剩训练约38–45分钟，预计13:45–13:53UTC结束，评估后北京时间22:15–22:45释放估计保持。
证据：research/hold-20260929/receipts/backup-replication.json, research/hold-20260929/receipts/backup-integration.json, research/hold-20260929/receipts/monitor-latest.json。下一步：完成最终权重，核查冻结评估接续；留足报告视频发布时间。

## 2026-09-29T13:28:24.280808+00:00 followup_live_revalidated

13:27UTC重新实查四组训练仍运行，追加进度86–90%，四H100瞬时76–91%；预计13:47–13:54训练完成，后续冻结评估预计14:15–14:45释放。未重启实验，不追加训练。离线权重索引增加显式published开关，训练源码未动。
证据：research/hold-20260929/receipts/monitor-latest.json, scripts/index_wuji_hold_weights.py。下一步：完成既有训练、冻结评估、独立复算和交付，实查空闲后告知用户释放。

## 2026-09-29T13:39:17.351183+00:00 followup_delivery_tools_ready

新增离线汇总scripts.summarize_wuji_hold_followup（仅在两份独立复算均完成后运行）与scripts.package_wuji_hold_integration_video（渲染队列完成后运行）；逐源50%门槛、复验差值、物理回合去重及视频原始manifest均显式保存。未修改在训源码。13:39UTC训练继续，暂无后续冻结结果。
证据：scripts/summarize_wuji_hold_followup.py, scripts/package_wuji_hold_integration_video.py, research/hold-20260929/receipts/resource-1329.json。下一步：训练结束核验CP2000/3000，完成既有队列后运行离线汇总、视频打包和发布。

## 2026-09-29T13:48:04.914492+00:00 checkpoint_backed_up

hold_integrate_singleton_seed2903:3000 remote/local SHA and CPU integrity passed; 57e4ecfd49e77ff2705576695bf8a636c81daaa8f66c50eddc5d529b500f6c27
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:48:26.724675+00:00 archive_waiter_read_failure_recovered

13:48UTC发现后续归档等待器此前读取心跳status.json时JSONDecodeError（写入瞬间空内容）退出；没有开始归档、无上传覆盖。保留archive-followup.log，离线等待器增加原截止内15s重试，重启仅归档等待器。单源整合训练已完成且CP3000 SHA/CPU检查通过，所有训练和评估不重启。
证据：runs/hold-20260929/archive-followup.log, scripts/archive_wuji_hold_when_done.py, research/hold-20260929/receipts/backup-integration.json。下一步：重新归档四组全部权重日志并上传，继续既有冻结评估队列。

## 2026-09-29T13:48:27.602520+00:00 completed_training_archive_started

hold_integrate_singleton_seed2903 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T13:49:28.884029+00:00 checkpoint_backed_up

hold_r3_dense1_seed2902:2000 remote/local SHA and CPU integrity passed; 3c784fac57944fe184c89d0d541436511caaac83c8fd2836f6352f80dc39a882
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:49:59.506081+00:00 completed_training_archive_uploaded

hold_integrate_singleton_seed2903 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_integrate_singleton_seed2903.json, research/hold-20260929/receipts/hold_integrate_singleton_seed2903-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T13:50:21.989822+00:00 checkpoint_backed_up

hold_r3_original_seed2902:2000 remote/local SHA and CPU integrity passed; 71ad9ddd546db0cbbc67546aaecbf8fac6844a7a88c054ad690c8612d510c52e
证据：research/hold-20260929/receipts/backup-replication.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:50:30.272236+00:00 completed_training_archive_started

hold_r3_original_seed2902 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T13:51:45.724787+00:00 completed_training_archive_uploaded

hold_r3_original_seed2902 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r3_original_seed2902.json, research/hold-20260929/receipts/hold_r3_original_seed2902-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T13:51:45.725008+00:00 completed_training_archive_started

hold_r3_dense1_seed2902 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T13:52:56.756922+00:00 completed_training_archive_uploaded

hold_r3_dense1_seed2902 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_r3_dense1_seed2902.json, research/hold-20260929/receipts/hold_r3_dense1_seed2902-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T13:55:30.637389+00:00 completed_training_archive_started

hold_integrate_shared_seed2903 completed; preserving all trainer weights and logs
证据：research/hold-20260929/preregistration.json。下一步：Verify archive SHA and upload immutable draft assets。

## 2026-09-29T13:55:50.782387+00:00 checkpoint_backed_up

hold_integrate_shared_seed2903:3000 remote/local SHA and CPU integrity passed; 1829aeac7a186ef1b9f63ffb7c5464f60746bbe41ac4e1eef1ad30b9a6a78664
证据：research/hold-20260929/receipts/backup-integration.json。下一步：Continue bounded training and frozen evaluations。

## 2026-09-29T13:56:10.879162+00:00 integration_video_started

video-integration-singleton-fixed5: four fixed source trial0 rows, local4090 separate render
证据：research/hold-20260929/integration-video-plan.json。下一步：Render actual final policy; retain every source outcome。

## 2026-09-29T13:56:38.370810+00:00 completed_training_archive_uploaded

hold_integrate_shared_seed2903 all trainer weights/logs archived; server SHA verified
证据：research/hold-20260929/receipts/release-hold_integrate_shared_seed2903.json, research/hold-20260929/receipts/hold_integrate_shared_seed2903-archive.json。下一步：Finish frozen comparisons; keep draft unpublished until final evidence and report。

## 2026-09-29T13:56:59.668470+00:00 all_followup_training_completed

四后续训练已全部完成：singleton13:47:25、dense复验13:49:05、original复验13:49:35、shared13:55:15UTC；各新增1000轮/163840000交互，最终CP2000/3000四权重SHA和CPU完整性通过，全部4完整权重日志归档已上传服务器SHA通过。GPU3无本轮任务；GPU0/1开发评估、GPU2整合冻结评估；本机四抓姿视频开始。告知用户再约25–40分钟释放全部开发机GPU，不再训练。
证据：research/hold-20260929/receipts/backup-replication.json, research/hold-20260929/receipts/backup-integration.json, research/hold-20260929/receipts/monitor-latest.json, research/hold-20260929/weights-index.json。下一步：完成冻结评分与独立复算、视频检查、资源释放、最终发布。

## 2026-09-29T13:57:26.062119+00:00 integration_video_completed

video-integration-singleton-fixed5: strict 1/4; individual source outcomes recorded
证据：runs/hold-20260929/video-integration-singleton-fixed5/evidence/report.json。下一步：Inspect frames and archive videos/raw traces; do not replace frozen512 metrics。

## 2026-09-29T13:57:26.123059+00:00 integration_video_started

video-integration-shared-fixed5: four fixed source trial0 rows, local4090 separate render
证据：research/hold-20260929/integration-video-plan.json。下一步：Render actual final policy; retain every source outcome。

## 2026-09-29T13:58:41.296941+00:00 integration_video_completed

video-integration-shared-fixed5: strict 1/4; individual source outcomes recorded
证据：runs/hold-20260929/video-integration-shared-fixed5/evidence/report.json。下一步：Inspect frames and archive videos/raw traces; do not replace frozen512 metrics。

## 2026-09-29T13:59:46.913834+00:00 integration_videos_packaged_verified

两段本机四源视频已逐步独立复算并检查固定帧，两组均仅源3严格成功1/4。打包首次因系统PATH无ffmpeg失败，改用已有imageio_ffmpeg；未重仿真、已复制文件SHA一致后续接成功。原始视频/时序保留。
证据：research/hold-20260929/video/integration-video-results.json, research/hold-20260929/video/integration-inspection.json。下一步：上传两视频和原始归档，等待冻结512结果再形成整合结论。

## 2026-09-29T14:01:52.921705+00:00 replication_development_frozen

第二续训种子开发集原奖励选CP1500、改动选CP2000；最终同预算仍CP2000固定，开发选点单列。GPU1开发评估完成，GPU0等待器进入最终128评估；GPU2整合继续。
证据：research/hold-20260929/receipts/replication-development-selection.json。下一步：完成既有最终测试，保持所有失败和不同CP选择的区别。

## 2026-09-29T14:21:28.516531+00:00 integration_frozen_independent_rescore_completed

Shared-policy and singleton controls raw SHA verified and independently rescored per source
证据：research/hold-20260929/receipts/raw-integration.json, research/hold-20260929/analysis-integration/report.json。下一步：Report every source and preserve prior successful expert; inspect representative actual video and complete delivery。

## 2026-09-29T14:22:20.748875+00:00 core_frozen_evidence_collected

Source3 seed2902: development and final raw evidence mirrored; every remote/local file SHA verified
证据：research/hold-20260929/receipts/raw-row3-seed2902.json。下一步：Independently rescore both sources before followup decisions。

## 2026-09-29T14:22:26.016917+00:00 core_frozen_independent_rescore_completed

seed2902 sources [3] independently rescored; matched-budget and selected results remain separate
证据：research/hold-20260929/analysis-seed2902/report.json。下一步：Inspect all counts and endpoint diagnostics; apply frozen followup criteria。

## 2026-09-29T14:23:13.498378+00:00 remote_gpu_released

14:23UTC实查开发机4H100均0%、1MiB，无计算PID，无本轮训练评估进程。全部冻结结果独立复算通过，第二种子源3原24.609375%改92.96875%；整合源3成功但原0/1/2全部0，未通过联合门槛。告知用户开发机已释放；仅本机报告、上传与发布继续。
证据：research/hold-20260929/receipts/remote-released.json, research/hold-20260929/followup-summary/report.json。下一步：完成资源核算、最终报告/交接、公开Release验证与独立分支push。

## 2026-09-29T14:25:03.539723+00:00 owned_monitor_stopped

本轮训练/评估/备份/收集/归档/渲染队列全部完成，仅自建只读monitor仍存活；核验PID1521593命令与cwd后SIGTERM停止，不影响其它任务。
证据：research/hold-20260929/receipts/monitor-stopped.json。下一步：最终报告及发布，开发机保持释放。

## 2026-09-29T14:27:32.221573+00:00 final_conclusions_verified

所有预定实验及条件后续已完成，源3两续训种子奖励改动有效；源11未解决；共享保留源3但未获得原0/1/2技能，body在首秒附近失稳。30资产/32正式CP/8视频及原始时序均保存。下一步唯一研究优先为源11到位后保持与支撑协同受控修复；当前只做最终发布，不再计算。
证据：research/hold-20260929/README.md, research/hold-20260929/followup-summary/report.json, research/hold-20260929/analysis-integration/body-breach-timing.json, research/hold-20260929/receipts/assets-final-draft-verified.json。下一步：最终commit/push、公开Release和下载哈希核验，完成本轮有界Goal交付。

## 2026-09-29T14:30:27.146357+00:00 release_published_verified

Release wuji-hold-20260929-v1已正式发布，30资产服务器SHA逐项匹配，8视频均无认证公开下载SHA通过。实验结果提交55bccd0已push；最终发布索引/交接提交中。源3改善两续训种子复现，源11与共享原抓姿未解决，行为目标只部分达成。开发机14:23UTC已释放，本轮无剩余计算。
证据：research/hold-20260929/receipts/final-release-verified.json, research/hold-20260929/receipts/public-video-downloads.json, research/hold-20260929/weights-index.json。下一步：提交最终发布记录并核验分支，结束本轮有界实验；后续唯一优先为源11到位后保持与支撑协同。

## 2026-09-29T14:31:34.892582+00:00 bounded_goal_delivery_complete

本轮有界实验交付完成：GitHub API确认分支3c2a0e992cdfee624fab75841b7eb652884d72fc，Release正式公开30资产/8视频下载SHA核验，无剩余计算或交付任务。行为目标部分达成，不宣称源11或统一策略已解决；本次只提交此收尾续接记录。
证据：research/hold-20260929/final-delivery.json, research/hold-20260929/receipts/final-release-verified.json。下一步：本轮结束；若继续新实验，唯一优先源11到位后保持与非拇指支撑协同。
