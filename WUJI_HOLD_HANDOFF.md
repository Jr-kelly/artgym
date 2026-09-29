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
