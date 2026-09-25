# Wuji 美工刀持续实验交接

更新时间：2026-09-23T13:43:29.510395+00:00。**顶部是当前事实，后面的历史快照只作追溯；PID、CP和利用率必须实时核验。**

## 新会话入口

- 实际实验根 `/data/research/artgym-experiments-20260921`（非Git）；原仓库 `/data/research/artgym` 保留。本文镜像在原仓库根，远端副本在 `/home/wangjiarui/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md`。
- 先读本文，再读 `runs/wuji-goal/goal-state.json`、`runs/wuji-goal/health/LATEST.md`，逐事件流水 `runs/wuji-goal/journal/events.jsonl`。
- 原本机训练 **88339** 不可停止。不得创建子代理。所有在途实验源码已固定，不能原地修改pin；失败和取消均保留，新尝试用新目录。
- SSH `.106:30147` 与 `.93:30147` **仍是同一八H100主机**，12:06再次核验hostname、boot ID、全部GPU UUID相同；四卡为`.73:30296`。完整连接命令见下方“机器与路径”。
- 仅运行有用计算。平台4小时GPU利用率门槛26%，目标>40%；最近13:19 UTC四卡4h52.86%/5min62.36%，八卡52.60%/53.43%。健康monitor **3132243** 每5分钟查。
- 工具goal仍显示外部blocked，本会话无resume工具；官方文档确认客户端命令 `/goal resume`（https://learn.chatgpt.com/docs/developer-commands?surface=cli）。用户已授权，实际训练/评估继续；不虚报complete。

## 最新接续：归一化训练对照与第二seed自动终审

- **冻结/更新输入统计配对已开始（13:41进入frozen臂PPO）**：四卡coordinator **286696**，`diagnostics/reset-normalizer-pair-20260923-v1/status.json`。已取得GPU2，所依赖机制22阶段完整审计通过，10000转移运行门禁已过；不改共享CP池。spec `reset-normalizer-pair-20260923-v1-spec.json`，suite `wuji_reset_normalizer_pair_20260923_v1_suite.json`，sourceSHA `ad03ffc10e35e0b1f9d91636b5c310982a7edbc447f678db03900612673d5c7a`。两臂都从原teacher/normalizer、新Adam、seed20261129、LR1e-5、2x初态扰动、5120×32×100开始；唯一干预是input normalizer冻结/更新，actor/critic/value统计继续学习。顺序frozen后adaptive；run `wuji_bridge3_reset2x_norm{frozen,adaptive}_seed20261129_v1`。训练代码默认不变；新flag只在此spec开启。
- 新模式本机和远端3个CPU单测通过，`diagnostics/reset-normalizer-code-validation-20260923-v1/report.json`：反复train/eval切换保持全部输入统计逐元素一致、仍有actor梯度与参数更新、value统计更新、默认与显式False相同。第一次测试误入原仓库editable模块、第二次tests命名空间冲突均发生在0物理/0训练；最终使用pin的runtime_environment+unittest discover，失败原因保留。正式每臂仍需实际10000转移门禁、3轮PPO预检核查normalizer/actor/critic/value，再重新从起点训100轮。
- **归一化CP评估改八卡GPU0**：coordinator **64822**、五分钟独立复算 **64823**，状态 `diagnostics/reset-normalizer-evaluations-eight-20260923-v3` / `reset-normalizer-cp-audit-monitor-eight-20260923-v3`；队列 `reset-normalizer-evaluation-20260923-h100-v3-queue.json`，sourceSHA `eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09`。等待既有GPU0 CP worker结束后取得整队列租约；所有44条件统一同GPU、batch332、seed20261125，重测冻结基线，不能混入本机332成绩。保留八卡容量helper，它只租GPU1/3/4/5，因此互不抢同一租约。旧本机712869/712870于0评估/0审计取消，证据保留；v2只准备未启动，v3显式记录H100评分协议标签。
- **第二seed自动终审710101**：`diagnostics/reset-seed2-finalization-20260923-v1/status.json`；spec `reset-seed2-finalization-20260923-v1-spec.json`；sourceSHA `a44bf9c7a87dee89dcb6ddc2bc905fcd7944b3dbe0a1cb3cfbacfd2f78e8ecc0`。等全44后回传已完成训练日志/门禁，核查两臂实际预算和CP，再分析/打包/上传并校验digest。只复算与归档，不重跑物理。
- 机制诊断13:30部分审计：原teacher/CP25/50/100快速261/264/252/258，CP50/100用原统计262/266，原权重换CP100统计229，固定初始目标0但刀身稳定278（均/300）。前三个慢速原/CP25/CP50为267/278/280。尚待全部慢速，不能将反事实拼接控制器当成新训练成绩；body与完整开合区分。
- 全局源码212205已完成共享远端回读SHA核验：`source-snapshot-20260923T212205.tar.gz`，SHA `285c6829de3eef02b8b306ab324151120f193a9d18c25b8ded571318f02681ed`。此版本早于本段新归一化/终审代码；各新实验以各自pin为准，下一步重做全局快照。

### 13:41 UTC 冻结机制完整结论

`diagnostics/reset-mechanism-gpu2-audit-monitor-20260923-v3/audit-22-20260923T134059Z.json` 独立复算全部22阶段、3,198,000转移和正常退出。原teacher快/慢261/267；CP100原生258/278，换原统计266/282；原权重换CP100统计229/258。CP50原生252/280，换原统计262/279。固定初始目标两时钟均0任务成功、278/300刀身稳定，0.5秒时280稳定。第四始终0/32。这支持统计漂移会改变控制，但不支持“换回统计即可解决”：慢速CP50甚至-1，仍有身体和端点缺口。固定持握本身也不是所有行都稳定；动态控制可救回部分行，不能将22个固定持握失败说成机械不可行。

独立审计/原始轨迹正在同步本机；离线总结脚本 `scripts/analyze_wuji_reset_mechanism.py` 与bootstrap helper已固定到 `source-pins/reset-mechanism-analysis-20260923-v1`，尚待运行/查看/上传新图。分析不是额外物理实验。归一化新PPO结果尚未评估，不能用本段反事实结果代替。

## 已确认的结果

以下成功数分母均为三个已训练抓姿各100状态；另32个旧第四抓姿始终保留，仍0/32。视频/旧开发/独立新初态/真机严格区分。

|冻结模型与数据|2秒换命令|5秒换命令|结论|
|---|---:|---:|---|
|混合RGB，主独立新小扰动|287/300|294/300|通过当时95%总体、每组90%的工作门槛；非新抓姿/几何/真机|
|同RGB，另300个两倍扰动|237/300|255/300|未通过；此批现已作为诊断/适应开发集|
|同teacher，真实物体状态，两倍扰动|258/300|266/300|未通过；抓握/控制也有缺口|
|真实位姿重建+因果速度，两倍扰动|253/300|263/300|速度估计不能解释主要失败|
|独立sensor运行时实际控制，旧小扰动开发集|288/300|295/300|软件接口全332状态验证通过，非新的独立验收|

- 主独立：`diagnostics/rgb-independent-final-rescored-1802-v1.json`及统计/解释`research/wuji-rgb-independent-result-20260923.md`（均在runs/wuji-goal下）。同刀同相机、三已训练抓姿，±.5mm位置/±.01rad关节/±.5度旋转分量；无结果筛选。
- 压力集：`rgb-wider300-total-seed20261123-v2/mixed332.npy`，SHA `ecb5989f1739a346f4fed5f174a98261737a069d94bff45a753538466168e025`。幅度±1mm/±.02rad/±1度。主独立模型和指标未改。
- 完整oracle：`diagnostics/reset-oracle-wider-2005-v1` 全16阶段正常退出、796800转移独立审计 `reset-oracle-all-rescored-20260923-v1.json`。同配置、同初始观察、同4×83批和种子；只减少无控制用途的渲染频率。不是可部署策略。launcher72925/finalizer137543均已完成。
- teacher慢速34个失败全部涉及身体稳定；身体稳定的266全到位。快速37个身体失败+5个稳定但不到位。只有11个身体失败发生在前.5秒，其余涉及操作中的失稳。证据`reset-oracle-teacher-decomposition-20260923-v1.json`、`reset-oracle-teacher-failure-times-20260923-v1.json`。
- 传感器接口：`rgb-sensor-active-parity-development-1924-v1`及`rgb-sensor-active-final-rescored-1937-v1.json`，398400转移已审计；旧launcher268864/finalizer269972完成。输入RGB/编码器/URDF FK/外部命令/已知初始化，自持动作与目标历史，不读当前物体真值。活动mask仅作断言，退休失败仍计失败。
- CPU计时：`rgb-sensor-cpu-latency-1953-v1/results.json`，CoreUltra7/1线程，p50=4.69ms、p95=5.83ms、p99=6.35ms，未计相机/通信/电机，不是CPU闭环或硬件验证。

## 当前运行与接续

- **四卡Wuji续训已完成**：coordinator旧276244于12:32结束；1x和2x两臂均100/100、所有CP10/25/50/75/100保存且下载SHA一致。实际32,768,000正式转移，另每臂491520预检+10000运行门禁。日志/权重/预算审计 `diagnostics/reset-range-training-final-audit-20260923-v2.json`；两臂源码、起点、seed、预算相同，只改变重置扰动。旧teacher278447已退出。
- 训练源pin `/home/wangjiarui/artgym-pinned-reset-range-pair-20260923-v2`，archiveSHA `a63fc2544ff410d330a3f0ca000961f617bac0f62453f82eb9cc946963256efc`，manifestSHA `aac5a520d1037f9272c656ae754f60652b758f47bddb3d34ce216a23a51dc68f`。suite `wuji_reset_range_pair_20260923_v2_suite.json`、spec `runs/wuji-goal/reset-range-pair-20260923-v2-spec.json`。只在线扰动3个训练抓姿，不采样评估行。
- **本机CP自动评估**：第一seed下载协调器 **164055已完成**、evaluator **210085已退出**，`diagnostics/reset-range-local-evaluations-20260923-v3/status.json`。每20秒查远端不可变policy快照，SHA核验后原子落盘；与原88339共用本机GPU0，oracle结束后已开始。CP10 SHA `b13713ffa7714171b8b0b09ee9aa095cfacb3ab3b5cc04ef065f6dc3400a2e0b`；其他SHA在downloads字段。
- CP队列 `reset-range-evaluation-20260923-local-v3-queue.json` 共44条件：冻结原teacher基线+两臂CP10/25/50/75/100，各旧小扰动332和已观察大扰动332、2s/5s命令。目录 `verification/reset-range20260923-*-local-v3`。这是**本机批332**协议，须以同协议冻结基线对比，不能混用4×83/H100数值。已发布主独立集不用于选新CP。
- **CP独立复算monitor303147**：每5分钟只在有新完整条件时复算，`diagnostics/reset-range-cp-audit-monitor-20260923-v2/LATEST.md`和status；评分源码固定在`source-pins/reset-range-cp-audits-20260923-v1`。44全部完成后出完整审计，未齐仅partial，不能挑早期峰值。
- **四卡参考训练**：原corrected Sharpa GPU0/3、launcher106419保持，最近CP5250。机制v3已结束并恢复CP池[2,1]、scheduler **287262**；新归一化训练租用GPU2；既有GPU1 CP5250 worker保留。Wuji第二seed284122只等待GPU1租约，不改池。机制v3已于13:38完成恢复；训练租约持续防止重叠，届时须核验新PID。
- **八卡参考训练**：原upstream GPU6/7；seed2 upstream22713 GPU1/3、corrected22714 GPU4/5继续。CPscheduler当前37338、池[0,2]。**资源接续helper44720** `diagnostics/eight-after-seed2-capacity-20260923-v1`：仅等两seed2结束、GPU1/3/4/5显存释放且拿到租约，才把CP池扩成[0,2,1,3,4,5]；保留所有现有worker，填补有用评估负载。其他工作要用这些卡前先检查该helper状态。
- 预检KL解释：suite的.05门槛读的是聚合`info/kl`，2x预检.03576/.02440/.02011，不等于同策略更新距离。它只是已记录的入场检查；若1x因此失败，保留失败、先核验同组精确KL再开新尝试，不据此归因。

- **冻结机制诊断v3 282851（GPU2），复算282861**：`diagnostics/reset-mechanism-gpu2-20260923-v3/status.json`，sourceSHA `37d416fce431eb88864a25044d2b2d63cd62023fe12ff3187295b55c9d539d04`，spec `reset-mechanism-gpu2-20260923-v3-spec.json`。6个运行门禁已正常通过（13:12核验），已进入16正式条件：原teacher、2xCP25/50/100，CP50/100配原输入normalizer，原权重配CP100normalizer，以及恒定初始目标持握；同H100GPU2/batch332宽开发集2s/5s。两时钟的no-op必须与native完整trace逐元素相同。诊断控制器不当作新学习策略成绩。CPU复算采用固定pin `artgym-pinned-reset-mechanism-audits-20260923-v1`，archiveSHA `86f07368f88532c57821bc9da1a6c44a9bef61236c771fcfbeb662bb6742c051`，最新在 `diagnostics/reset-mechanism-gpu2-audit-monitor-20260923-v3/LATEST.md`。
- **完整CP终审/发布432601已完成（43/43资产digest核验）**：`diagnostics/reset-range-finalization-20260923-v1`，监控44/44已结束，最终控制分析/曲线、全部原始trace和11个冻结权重已打包上传，43项GitHub digest均核验；验证 `diagnostics/release-reset-range-pair-complete-20260923-verified.json`。pin `source-pins/reset-range-finalization-20260923-v1`，sourceSHA `92261dc8dbe52ad5c4f1d684635de31b0b5370f4495706172385050d72ae248a`。不要把waiting或部分上传说成完成。

- **Wuji第二训练seed284122（13:30已开始正式1x训练）**：`diagnostics/reset-range-seed2-20260923-v2`，已在CP5250结束后取得GPU1独占租约，实际10000转移门禁和3轮PPO预检均过；不改CP池，避免与GPU2诊断互相覆盖。同原冻结CP25、normalizer、新Adam、LR1e-5、5120×32×100/臂，只换seed20261128；顺序1x后2x。源SHA `ff94128c8c14782b86c804c62dd169187ae57c2abdef4e5a2b02a67e14637088`，suite `wuji_reset_range_seed2_20260923_v1_suite.json`。下载508717、5分钟复算557077；第二套本机44条件排在第一套44评估结束后，保留原88339。状态 `diagnostics/reset-range-seed2-local-evaluations-20260923-v1` 和 `diagnostics/reset-range-seed2-cp-audit-monitor-20260923-v2`。

新增失败/调度记录：机制v1在0物理/0审计时取消，因GPU2空闲改位置；第一次取消检查把已知scheduler子进程误当物理子进程而拦下，未做任何变更。v2的native与noop各1800物理转移全部10个trace数组逐元素相同，但noop退出1：旧固定评估器没有cleanup hook，所以未写intervention.json。v3只改为base正常返回后验证独立模型张量并保存元数据，重跑全部门禁；不改物理/控制/阈值。旧v2完整trace与失败保留，不计正常通过。当前CP池/诊断PID必须读实时status；旧入口PID280251/281520已取消、282017已失败退出。

接下来按数据决策：完成两臂全部CP/两时钟/两开发集；先看身体稳定和端点的拆分，再选择候选。若teacher宽扰动可靠，再复核其与RGB估计器的组合，并按需要收集新teacher/自身轨迹更新视觉；**冻结后另生成新独立初态**验收，不能把当前压力集重新称独立。若teacher仍失稳，先查早期与循环中掉落、支持指控制范围和物理持握，不盲目延长训练。真机尚无SDK闭环，摩擦/阻尼与初始化误差待实测。

### 首轮配对续训最终结果（13:19 UTC全部44条件已独立复算）

审计 `diagnostics/reset-range-cp-audit-monitor-20260923-v2/audit-44-20260923T131828Z.json`，共8,764,800评估转移，全部正常退出。控制分析/完整CP曲线 `diagnostics/reset-range-control-analysis-final44-20260923-v2`；PNG已人工查看，显示所有预定CP，没有挑峰值。以下均本机batch332已观察开发集，每项分母300；第四始终0/32。

|模型|小扰动快/慢|两倍扰动快/慢|两倍扰动刀身稳定快/慢|
|---|---|---|---|
|原冻结teacher|298/299|252/263|258/264|
|1x续训最终CP100|282/282|242/252|259/274|
|2x续训最终CP100|294/298|262/279|274/284|

2x在所有五个预定CP的宽扰动快/慢均高于同预算1x，但只有一个训练seed；第二seed正排队复核。没有候选同时通过两时钟95%门槛。CP25→50的快速退化主要是刀身稳定时端点偏离增多，不等于掉落增加。支撑限幅相关性和normalizer变化均不能单独证明原因。

### 持续文档镜像

本机进程 **760633**（v2，旧614197已停止）每5分钟将交接入口、goal-state、事件流水、健康摘要/注册表以及本机负责的五组协调器/审计状态做稳定字节快照，rsync到共享远端并回读SHA核验。状态 `diagnostics/handoff-mirror-20260923-v2/status.json`；spec `handoff-mirror-20260923-v2-spec.json`；固定脚本 `source-pins/handoff-mirror-20260923-v2/mirror_wuji_goal_handoff.py`，SHA `e70ae2181a04c11fe90114a3537122cdc848d9c3b99f817b6fd61d8bdf8a9067`。v2每周期读取健康注册表的local_runs，后续新增本机监控可自动纳入；远端所属任务绝不添加进local_runs。它不覆盖远端训练状态/CP调度配置，也不替代源代码快照；远端实验运行结果仍需回传。

## 发布与恢复材料

Release：https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921 ，用户授权全部可视化命名上传，视频无文字。
已核验：主独立16/16、混合开发38/38、自主3旧状态视频10/10、H100运行库4/4、宽扰动12/12、完整sensor18/18。各`release-*-verified.json`保存GitHub digest。

完整oracle **16/16资产已上传并核验**（旧上传PID226614完成）；核验`diagnostics/release-reset-oracle-complete-20260923-verified.json`，完整archiveSHA `d35a78a049a3735e4c48c512d046d0749804f6771acb3861fdb279438601deee`，567669162bytes/9卷。最终核验文件已存在。

最近全局源快照211253：`runs/wuji-goal/source-history/source-snapshot-20260923T211253.tar.gz`，SHA `96d31def78b834b805edfa8ebd7d601ae1b325eee8218f52792cfd1367924f66`，2556文件，archive逐项验证；包括机制v3/第二seed等待/终审发布源码。已安排同步远端共享文件系统。同步源文件用`source-sync-files.txt`，排除root所有*monitor*.json和runs里*status.json；health registry单独同步。pin的runs符号链接不可展开。

本轮失败/取消：压力生成v1路径错误在0状态失败；oracle终审v1缺scheduler模块在0审计失败，v2自包含helper已完成；GPU1被参考训练租用的八卡新CP队列41016在0计算取消；等待GPU2的Wuji coordinator275211在0训练取消后改空闲GPU1；本机旧下载协调器147451在0下载取消后改新训练v2路径。全部证据保留，勿重启旧PID或覆盖旧目录。

下面为历史背景与细节，冲突时以上面当前入口及实时status为准。

## 目标和边界

用户授权持续执行研究/训练，直到学习策略在 Wuji 上通过**新独立初态**的完整开合评估，再扩大抓姿、几何和物理变化并向真机推进。目标尚未完成。脚本视频、特权 teacher、旧开发成功率、离线误差和3状态运行预检均不等于独立成功，更不等于真机成功。

实验根 `/data/research/artgym-experiments-20260921`（非 Git），原仓库 `/data/research/artgym` 保留。本机原训练 PID **88339** 不可停止。不得创建子代理。运行实验必须使用不可变源码 pin；所有失败保留，新尝试新目录。IsaacGym先于torch导入；模拟子进程通过`runtime_environment`配置，远端GPU用`acquire_evaluation_gpu`租约，不能绕过已有工作。仅有用计算；平台整机4小时利用率门槛26%，运行目标>40%。

工具 get_goal 仍为旧 blocked，工具没有恢复 active 的接口；用户已明确授权继续，实际执行持续。不能虚报 complete 清除状态。

## 机器与路径

远端根 `/home/wangjiarui/artgym-experiments-20260921`，Python `/home/wangjiarui/artgym-runtime/bin/python`。本机Python `/home/agiuser/miniconda3/envs/artgym/bin/python`。

```bash
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.106
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.93
ssh -p 30296 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.73
```

**106与93是同一八卡H100机器两个入口，不是16卡。** hostname `d-20260921021501-6zzgt`，boot `70711c34-b51c-4565-bdb5-d45efa916f63`。四卡hostname `d-20260920124121-d9ns7`，boot `57bb1417-d6fa-4a1c-a8f2-eb7baa9a445d`。两机共享 GPFS 文件，但 PID 不共享。远端无 rg。

## 历史执行快照（10:42 UTC，已被顶部最新段覆盖）

- 本机新独立配对评估 **3577326**：`diagnostics/rgb-independent-paired-1729-v1`，已10/16，baseline5s-part1在跑。原/混合两冻结RGB模型×2s/5s×4批83，必须全齐。**保持本机既定协议，不迁移H100、不按当前结果调参。**
- 本机自动终审 **3757032**：`diagnostics/rgb-finalization-1802-v1`，pin `source-pins/rgb-final-audits-1802-v1`。等全16后写 `rgb-independent-final-rescored-1802-v1.json` 和 `rgb-independent-final-statistics-1802-v1.json`，检查真实exit0、原始轨迹、权重/初态SHA、Wilson区间和配对bootstrap。
- 四卡：自主传感器3门 **1823-v4已全部完成**，扩大332的 **1832-v1已失败**，不要重启旧PID。当前离线差异重放队列 **265871** 等GPU1已有CP结束，日志`diagnostics/queue-sensor-replay-1849.log`；结果目标`rgb-sensor-discrepancy-replay-warmed-1848-v2.json`。
- 四卡CP scheduler已从181724换成 **265810**，配置`sharpa_corrected_recovery_monitor.json`池暂为[2]；GPU1给传感器诊断/全评估，原CP worker未停。证据`diagnostics/four-gpu1-sensor-reservation-1849-v1`。**传感器工作结束后恢复池[2,1]，仅重启scheduler并保留workers。**
- 八卡图形三门 **29002**：`diagnostics/rgb-egl-eight-retain-driver-1758-v10`，仍待GPU0现有CP完成。此前被CP队列抢先，现有预约helper **33804**，`diagnostics/eight-gpu0-graphics-reservation-1845-v1`。八卡CP scheduler从23245换为 **33805**，`experiment_monitor.json`池暂[2]；helper会在图形三门完成或失败后自动恢复[0,2]并重启scheduler，届时PID会再变。
- 八卡Sharpa：原upstream GPU6/7，launcher1845/torchrun2530，最近CP3750/6250；第二seed upstream22713 GPU1/3、corrected22714 GPU4/5，最近CP100/500。每臂2×10000环境，全局20000，160M帧的第二seed对照，不是最终2B复现。
- 四卡原Sharpa corrected GPU0/3：launcher106419、workers106428/106429，最近CP4950/6250。
- 本机健康monitor **3132243** 每5分钟巡检，registry `goal_health_monitor.json`。最近10:33四卡4h45.01%、八卡重启以来47.83%/13490s，仍须刷新。原训练88339保持。
- 混合开发证据Release上传 **3893997**：`release-rgb-mixed-development-1828-verified[.pending].json`，10:37为16/38，未完全核验不能称全部发布。

上述`diagnostics/`均指`runs/wuji-goal/diagnostics/`。

## 已冻结的结果和独立验证协议

混合RGB旧开发全16条件、796800转移独立审计通过：`rgb-mixed-final-rescored-1802-v1.json`。

|模型|2s命令成功/300|5s命令成功/300|
|---|---:|---:|
|原RGB|268|294|
|混合RGB|290|297|
|原屏蔽图像|105|135|
|混合屏蔽图像|135|202|

混合RGB三组快96/97/97、慢98/99/100；第四旧抓姿所有条件均0/32（全程存活也0）。三组来自3个已训练抓姿的旧扰动，不能称新抓姿泛化。

混合拟合：`rgb-mixed-fitting-1705-v1`，36000 teacher图+36000原RGB自身轨迹图，原60/30初态行拆分，48000训练/24000验证；同初始化/同归一化，64+64 batch，5000 Adam步、LR2e-4、640000样本。拟合全部数据、优化器计数和最终权重已审计。

最终权重：混合RGB `9221141fe68ec6c116d0b30fab1415794a0eefa48b4c0e8591ba7afe00669d28`；原RGB `0c87d64951e7254d4e41ba891a95baebd17876614fc98e63b989fd67728be67a`。冻结teacher `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`，位于`frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth`。

新独立初态：`rgb-fresh300-total-paired-seed20261120-v2`，seed20261120，在两模型冻结后09:17UTC生成，三组各100无结果筛选的新扰动，行不重合校验；±0.5mm位置、±0.01rad关节、±0.5度旋转分量。第四32为重复失败对照。mixed332 SHA `d04d8a2759533bb50b5ef49802acd8144db0f8924ed3723eef618fae23815e0c`。预注册 `rgb-fresh-paired-1703-proposal.json`，每种时钟总体≥95%、每抓姿≥90%，报告Wilson与10000次分抓姿配对bootstrap。所有16项完成后再读最终结论；未完成不能挑阶段峰值。

## 传感器接口、数值差异与视频

`isaacgymenvs/deploy/wuji/rgb_policy_runtime.py` 的 `WujiRGBPolicyRuntime` 不创建物理环境、不连硬件。输入RGB、编码器q、URDF FK、外部目标、reset已知55字段和初始目标；自持过去动作/目标。CNN预测物体位移/旋转/滑块，因果差分alpha.25估速度，冻结actor输出20关节动作/目标；当前物体/接触真值不进入。

已完成：shadow `rgb-sensor-interface-parity-1812-v2` 5400转移；自主driver `rgb-sensor-autonomous-driver-1823-v4` 5400转移，各baseline2s/mixed2s/mixed5s在3个旧状态全3/3，正常退出。自主审计 `rgb-sensor-autonomous-gates-rescored-1837-v1.json`。3段实际控制视频各599帧、30fps、960×320、无文字，已检查contact sheet；视频仍待命名发布。它们是3状态预检证据，不是独立/真机。

固定v4 pin `/home/wangjiarui/artgym-pinned-rgb-sensor-driver-20260923T1823-v4`，完整archiveSHA `66e8f6830432920985104462301f2c2e7e23d75a9b9403d347505bafd9d99ac9`，manifestSHA `7c2fdb927433377216875dcc84174f7c50509d7d4e60d46159227e92b7bc326b`。

保留的失败：
1. shadow1807-v1错误自持未执行历史，27转移后失败；v2改用实际历史。
2. autonomous1817-v3未复现环境完整FP32 unscale→scale→平滑→限幅，39转移后目标断言失败，13帧视频**不是成功demo**；v4修正映射，没改模型/阈值。
3. full1832-v1第一83批2158转移后失败：action差0.00022073 >0.0002，policyobs差2.76e-6、state差5.96e-8、目标差4.71e-6。未调阈值。
4. diagnostic1839-v1在Python启动前缺libnvidia-glsi（预加载却漏LD_LIBRARY_PATH），0转移；1843-v2补库路径后复现相同失败并保存`formal-mixed-2s-part0/sensor-first-discrepancy.pth`，含两路输入、动作、循环状态。新pin archiveSHA `599d5bcc9eb0d1ffe45d31b04568a74963ffe2ae321bad6dbe6302ea840754bb`。
5. 离线replay1845-v1：reference动作逐位复现，但sensor动作仍差1.34e-4，说明重建输入/运行算术还有因素，**尚不能定论仅FK导致**。当前1848-v2检查TorchScript四元数kernel预热后的算术差异，再做FK/历史/估计状态分项替换。脚本`diagnose_wuji_sensor_discrepancy.py`。必须先定位，不静默放宽断言。

## H100渲染修复

四卡`rgb-egl-retain-driver-1755-v9`三门正常exit0，53400转移独立审计`rgb-egl-four-all-gates-rescored-1810-v1.json`。旧83成功76/83，本机77/83，存在不同数值运行结果，因此主独立验证保持本机。

只解包官方560.35.03匹配驱动到`diagnostics/h100-vulkan-isolated-1713-v2/runtime/usr/lib/x86_64-linux-gnu`，没有系统安装。使用EGL ICD；同时将隔离lib目录加入LD_LIBRARY_PATH，并用进程级LD_PRELOAD保留libvulkan.so.1、libEGL_nvidia.so.0、libnvidia-eglcore.so.560.35.03、libnvidia-glvkspirv.so.560.35.03、libnvidia-rtcore.so.560.35.03到退出。准确路径/哈希见v9spec。只改loader或显式销毁仍exit-11的v7/v8保留，不能忽略退出码或用os._exit掩盖。

取消CUDA_VISIBLE_DEVICES屏蔽，compute/graphics显式使用同一个物理ordinal，torch.set_device同步；只租用该GPU。launcher自身LD_PRELOAD也要求先设置隔离LD_LIBRARY_PATH。八卡待三门通过才能称该主机验证完成。

## 论文与物理事实

现实刀147×19×11mm、35g、50mm行程、40mm目标，Wuji20DoF，支撑指初始±.04rad，拇指每步±.025rad，阻尼.3未实测标定。严格判据20秒、30Hz控制/120Hz物理，外部每2s或5s换命令，每段末9帧误差<2mm，刀身全程<10mm/.25rad且有效存活。

纯关节DAgger续训最终快217/慢262（/300）；拇指loss×12同预算147/234差于未加权203/269，已不采用。TCN、GRU、历史状态估计等失败详见历史，避免无边界重复搜索。

Sharpa同CP3400/1.088B帧对照：upstream15764/28700=54.93%，corrected15475/28700=53.92%，差-1.01pp，配对抓姿bootstrap95%[-4.75,+2.78]。前50选择每几何top5、后50报告可达99.20%/99.92%，是选择诊断。论文Sharpa22DoF，功能抓姿、人工放置、privileged teacher、50帧TCN student、10mm到位，不包含桌面自主抓起；Wuji RGB是明确新增视觉的迁移路线，不是原纯本体TCN逐项复现。

参考分析：`research/sharpa-success-and-wuji-student-gap-20260922.md`、`research/wuji-vision-interface-review-20260922.md`、`runs/wuji-goal/research/wuji-rgb-progress-and-deployment-boundary-20260923.md`；论文`research/paper.txt`（arxiv2609.12498）。

## 发布、源码与下一步

目标Release：https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921 。用户已授权全部可视化命名上传，视频不加文字。已有DAgger/offline52、Sharpa12、原RGB38、joint continuation46项均哈希核验。混合新38项上传未齐。上传脚本`resume_wuji_release_upload.py`检查GitHub digest，不覆盖同名不一致资产。不要上传通用重名`package-status.json`。

全局快照`source-history/source-snapshot-20260923T182757.tar.gz` SHA `68dd553be69aedaa44f7744f814048bc267db0908786cf5b4512a4c1206c8194`，早于最新诊断/文档；各pin另有完整档案。复制pin用`symlinks=True`，`runs`链接禁止展开。归档校验gzip必须顺序`r|gz`避免反复随机seek。同步按`source-sync-files.txt`且排除**所有root *monitor*.json和runs里*status.json**，避免覆盖远端活动配置/状态；文档单独同步原根和远端。

接下来：
1. 读取1848 warmed replay结果；若未精确重放，保存sensor实际actor输入/归一化输入，再隔离算术/状态；禁止把数值预检失败归类任务失败或改阈值凑通过。
2. 保持独立全部16完成，审计终审和不确定性，明确三已训练抓姿小扰动范围。若冻结模型通过，再预注册更宽扰动/物理和几何检查；新结果不用于同一独立集重训练。
3. 完成sensor接口全旧开发332验证；当前83失败未完成。发布已审核3视频与失败、源pin和轨迹。
4. 八卡图形三门完成后预约helper自动恢复CP池，核验；四卡sensor工作结束恢复[2,1]。刷新每5分钟GPU窗口，不用空转负载。
5. 每次起止、配置/机器改变、成功/失败都更新本文、goal-state、journal，并同步原根/远端；源快照也补齐。保持已有原训练和正式参考训练。

### 2026-09-23T10:47:58.209525+00:00 数值根因已分离，等输入校验已排队

H100 GPU0离线重放1851-v3退出0：TorchScript四元数decode预热20次后sensor和reference动作均精确复现。替换FK造成1.38e-4动作变化、RNN历史造成8.32e-5；原2.2073e-4差异来自不同输入及历史，不是同图不同权重。新flag `--sensor-matched-reference` 对两actor使用同一sensor/FK/估计状态，独立RNN历史；仍单独比较sensor vs原PhysX观测/估计（2e-5）、动作/目标（2e-4），阈值不改，driver/runtime/权重不改。四卡GPU1 gate266502/full266503，run `rgb-sensor-matched-gate-1857-v1` / `rgb-sensor-matched-development-1857-v2`，pinSHA c4528801cba91cbcf2032916ad8223befdcec9848bc84c9de334f11c5b22922a。先3旧状态，再全部332旧状态，两时钟8条件。混合Release38/38已全部digest核验。独立已12/16（10:46），未改模型。

### 2026-09-23T10:51:24.909278+00:00 四卡传感器工作实际转到GPU2

由于GPU1完整CP5000仍在进行，原等待gate266502/full266503在**0计算**时取消并保存状态，重复离线waiter265871也取消。利用现有空闲GPU2启动相同pin的新run：`rgb-sensor-matched-gpu2-gate-1903-v2` PID266852；`rgb-sensor-matched-gpu2-development-1903-v3` PID266853。gate已到step330且action差0。四卡CPscheduler现在**266851、池[1]**，现有CP265488和所有训练均保留；sensorfull结束恢复[2,1]。新3段视频包10资产上传PID4026699，`release-sensor-autonomous-gates-1905-verified[.pending].json`，archiveSHA01cd30c860ec6ee77efc3885803356f2143ea96b80d60cdbbee85f7eece2aa51。独立13/16（10:50）。

### 2026-09-23T10:55:55.762220+00:00 GPU2全批再次预检失败，3视频已发布

1903 gate1800转移独立重算通过，action差0；full1903-v3在18094转移后以policyobs差0.0058717>2e-5失败（actor此前差0）。新diagnostic `rgb-sensor-lifecycle-1918-v1`捕获原PhysX观测、左右comparison张量、active/reset掩码；先验证是否已退休失败行被环境替换了缓存指尖位置，再处理生命周期校验。不能把整批视为已完成。3实际视频+证据10/10已Release哈希核验。新全局source185125 SHA8908381ecb55c708ce46919269909e591cdb7c8a11d6d96dfddc84574e969780已同步共享远端；源同步现在自动排除所有root监控配置和runs状态，gzip校验改成顺序读取。

### 2026-09-23T11:11:27.582113+00:00 八卡图形三门也完成，CP资源已恢复

八卡v10全部正常退出并独立重算53400转移：RGB3/3、masked1/3、旧83容量76/83，与四卡v9同样。证据`rgb-egl-eight-all-gates-rescored-1945-v1.json`。预约helper33804已完成恢复，八卡CPscheduler现在**37338、池[0,2]**；gate29002已完成，不再等待。主独立Release16/16已全部digest核验。最新全局源快照190905 SHA b076cf122a1504e45770d87aed60f189318987034fa3547c267532706b60957c 正在/已同步共享远端，早于本段正常。


第二seed复算monitor的v1在0审计时遇到协调器status创建竞态（早7ms读取），新v2允许status尚未出现并继续等待；评分代码/队列/阈值不变，旧失败保留。新PID 557077。


第二seed等待协调器v1在0门禁/0训练时取消：轮询间隙被Sharpa CP5250先取到GPU1。新v2 284122用阻塞flock线程排队、主线程维持心跳，不改共享CP池，不停止已有worker。实际训练计划尚未开始，run名称仍 `wuji_bridge3_reset{1,2}x_cp25_seed20261128_v1`；下载508717和复算557077继续使用原计划的44项队列，无需重启。


## 自动更新：两倍扰动配对CP完整审计与发布 2026-09-23T13:39:44.966290+00:00

44/44条件正常退出并逐条复算，全部CP/两时钟/两开发集已收齐。完整分析 `diagnostics/reset-range-control-analysis-final44-20260923-v2`。全部 43 个命名Release资产已核对GitHub digest，核验 `diagnostics/release-reset-range-pair-complete-20260923-verified.json`。这是已观察开发集的完整结果，不能代替冻结后的新独立验证。
