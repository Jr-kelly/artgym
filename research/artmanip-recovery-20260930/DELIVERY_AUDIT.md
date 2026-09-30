# 本轮交付核验表（实验进行中）

此表记录证据范围与未完成项；不是完成声明。最终交付时必须以当时实际文件、进程和远端结果重新核验。

|要求|目前可查证据|状态与缺口|
|---|---|---|
|完整目标、独立分支、起始及上游SHA|GOAL.md、STATE.json、UPSTREAM_AUDIT.md、Git提交|已保存；原工作区只更新续接文档，实验位于独立worktree|
|论文／上游／旧Wuji／新基线四列差异|UPSTREAM_AUDIT.md、upstream、各run的resolved.yaml和startup.json|已完成初始审计；后续方法变更要补充|
|动作映射、静态初态、专家与序列预检|reference-precheck、initial-analysis、BC数据审计和父权重归档|已有实际证据；不是目标能力验证|
|足量直接多抓姿RL|b-plan.json、learning.jsonl、rl250/500-integrity.json|已完成500检查点；累计1000/2000/3000/4000四段未完成|
|同起点M/E及最低3200预算|c-plan.json、bc800/1600/3200/6400-fit与integrity|已训练新增6400；下一段由验证与闭环证据决定，不能以短期S全零停训|
|完整趋势及固定末点|每段训练日志、逐来源F/S分析、checkpoint归档|持续积累；最终固定预算末点与选中点均须列明|
|有证据的后续实验|DECISIONS.jsonl、bc800-state-shift.json、rl250-analysis|尚无数据聚合或保持微调；原分支仍有改善时优先续训|
|同权重四来源推理、独立F/S|evaluate_wuji_recovery_batch、原始trace与独立summarize|开发评估已做；来源只用于采样/标签/统计。F存在循环且漂移，不等于S|
|新最终每来源128只开一次|data/manifest.json中final哈希|初态已生成；尚未传至远端或评估。先冻结模型/协议/选点，再开最终集|
|同批负责专家、计数、Wilson区间、构型簇|initial-analysis、各阶段report/trials/clusters|开发已具备；最终集仍待统一候选和专家同批比较|
|S64后第二种子，之后才student|gate_wuji_recovery、各stage-gates|尚未过S；第二种子/student未触发。不得称已完成部署观测验证|
|四来源同权重并排视频及代表失败|video-plan.json、package_wuji_recovery_video.py|脚本与固定开发rows已保存；实际渲染、逐例标签、失败例和视频检查未完成|
|模型/Adam/RNG/完整数据可恢复|阶段归档、restore receipts、weights-index.json|完成到BC6400实际解包与CPU恢复；后续checkpoint和最终索引仍需刷新|
|GitHub分支与独立公开Release|分支推送记录、draft-assets-verified.json|增量分支/草稿资产已上传；正式tag、公开下载SHA与下载后的恢复待最终交付|
|16h/24GPUh/max2与收尾预留|STATE.json、jobs命令、resources/latest.json、launcher预算检查|累计账实时刷新；需继续保留90min/2GPUh。超时余量按现有活动作业计入|
|资源利用率与最终清理|machine-gpu-history、report_wuji_recovery_resources|观测不足4h时不声称四小时达标；结束时核实仅本轮训练/监控退出，不能只凭历史PID|
|唯一推荐继续点与明确边界|HANDOFF.md、README.md|最终冻结后重写；当前仅固定仿真刀与已训练抓姿邻域、特权teacher，无真机/取刀/新形状声明|

最终审核必须确认每一行状态。能力失败可以如实交付，但不能以文档、归档或一次短评估替代尚有依据且预算充足的学习分支。
