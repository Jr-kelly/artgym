# Wuji 美工刀 goal：新会话接续入口

更新时间：2026-09-23T14:11:12.783890+00:00。此文件只保留当前入口；进程和GPU必须实时核验。

## 先读与约束

1. 实际实验根 `/data/research/artgym-experiments-20260921`（非Git），原仓库 `/data/research/artgym` 保留；本文件镜像在原仓库和共享远端根。
2. 再读 `runs/wuji-goal/goal-state.json`、`runs/wuji-goal/health/LATEST.md`；逐事件流水 `runs/wuji-goal/journal/events.jsonl`。旧交接全文已归档 `runs/wuji-goal/research/handoff-history-20260923T215219.md`，里面的PID不是当前事实。
3. 不创建子代理。保留本机原训练 **88339**。在途源码pin不可修改；失败/取消保留，重启用新协调器目录。IsaacGym先于torch；物理子进程使用 `runtime_environment`，远端拿GPU租约。
4. 用户授权持续研究、训练、修复和向 **Jr-kelly/artgym** Release上传命名可视化；视频无文字。仅运行有用计算，整机GPU 4h平台门槛26%，目标>40%。不能拿脚本、旧开发集或特权teacher成绩冒充独立/硬件验证。
5. 工具goal仍是外部blocked；本会话无resume接口。官方客户端命令 `/goal resume`（https://learn.chatgpt.com/docs/developer-commands?surface=cli）。实际授权工作继续，不虚报complete。

## 机器与路径

**`.106:30147`和`.93:30147`是同一八H100机器的两入口，不是16卡**；hostname `d-20260921021501-6zzgt`，boot `70711c34-b51c-4565-bdb5-d45efa916f63`。四卡 `.73:30296` hostname `d-20260920124121-d9ns7`，boot `57bb1417-d6fa-4a1c-a8f2-eb7baa9a445d`。两机共享GPFS文件，但PID不同。远端无rg。

```bash
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.106
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.93
ssh -p 30296 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.73
```

远端根 `/home/wangjiarui/artgym-experiments-20260921`，Python `/home/wangjiarui/artgym-runtime/bin/python`。本机Python `/home/agiuser/miniconda3/envs/artgym/bin/python`。不要直接用editable安装执行新实验，必须使PYTHONPATH指向相应pin和pin/rl_games；CPU单测用unittest discover避免tests命名空间冲突。

## 当前任务与PID（13:50 UTC核验）

表中diagnostics均在 `runs/wuji-goal/diagnostics` 下。

|主机|任务|进程|当前状态/入口|
|---|---|---|---|
|本机|原4090训练|88339|保持|
|本机|5分钟健康巡检|3132243|`goal_health_monitor.json`注册表|
|本机|文档镜像v2|760633|`handoff-mirror-20260923-v2/status.json`|
|四卡GPU1|Wuji扰动第二seed|284122|`reset-range-seed2-20260923-v2/status.json`，1x100完成，2x已CP50/100|
|四卡GPU2|冻结/更新归一化配对|286696|`reset-normalizer-pair-20260923-v1/status.json`，frozen100完成，adaptive正式启动|
|本机|第二seed CP下载/评估v2|809497（evaluator810714）|`reset-range-seed2-local-evaluations-20260923-v2`|
|本机|第二seed 5分钟独立评分v3|809498|`reset-range-seed2-cp-audit-monitor-20260923-v3/LATEST.md`|
|本机|第二seed自动终审v3|879492|`reset-seed2-finalization-20260923-v3/status.json`，等44齐|
|本机|归一化完整终审v3|879498|`reset-normalizer-finalization-20260923-v3/status.json`，等远端44齐并回传|
|八卡GPU0|归一化CP及时评估v3|64822|`reset-normalizer-evaluations-eight-20260923-v3/status.json`，已获得租约，实际基线运行中|
|八卡|归一化CP独立评分v3|64823|`reset-normalizer-cp-audit-monitor-eight-20260923-v3/LATEST.md`|
|本机|机制结果11资产上传v2|已完成|11/11 digest已核验，`release-reset-mechanism-complete-20260923-v2-verified.json`|

### 参考训练与资源

四卡原Sharpa corrected：GPU0/3、launcher106419，最近CP5350/6250。四卡CPscheduler **287262、池[2,1]**；两张卡当前被Wuji独占租约挡住，训练结束即恢复有用CP工作，不停止既有worker。

八卡原Sharpa upstream：GPU6/7，最近CP4100/6250。第二seed upstream22713占GPU1/3、corrected22714占GPU4/5，最近各450/500。CPscheduler **37338、池[0,2]**；64822排队接GPU0，不修改池。资源helper **44720** (`eight-after-seed2-capacity-20260923-v1`)仅等两参考seed2结束+GPU1/3/4/5空闲并取得租约，才把池扩为[0,2,1,3,4,5]，与新的GPU0预约不冲突。

13:44健康样本：四卡4h54.42%、5min50.36%；八卡4h53.41%、5min52.72%，无告警。平台计量口径与本机采样仍须区分。

## 当前训练的固定定义

### 第二训练seed：复核重置范围效应

- seed20261128；同原冻结teacher及normalizer、新Adam、LR1e-5、5120环境×32步×100轮/臂=16,384,000转移；先1x后2x。只在线扰动三个原始训练抓姿，不采样评估行。
- 1x位置±.5mm/关节±.01rad/旋转向量分量±.5度；2x翻倍。每臂10000实际转移门禁+3轮PPO预检，正式重新从起点开始。
- run `wuji_bridge3_reset{1,2}x_cp25_seed20261128_v1`；suite `wuji_reset_range_seed2_20260923_v1_suite.json`；训练spec `reset-range-seed2-20260923-v2-spec.json`。pin `artgym-pinned-reset-range-seed2-20260923-v2`，archiveSHA `ff94128c8c14782b86c804c62dd169187ae57c2abdef4e5a2b02a67e14637088`。
- 当前评估queue **`reset-range-seed2-evaluation-20260923-local-v2-queue.json`**。44条件=原基线+两臂CP10/25/50/75/100，各旧小/宽扰动、2s/5s。**单个条件名字仍保留-local-v1**，物理源码/初态/种子/阈值完全相同，队列v2只把未开始CP顺序改为1x在前。4个完整冻结基线逐字节复用：298/299、252/263，第四0/32。
- 13:49发现旧队列还先等尚未训练的2x，因此旧下载508717、等待evaluator605042、评分557077、终审710101已在无物理子进程时停止；0个CP物理被中断，旧目录保留`cancelled_waiting_for_wrong_arm_order`。证据 `reset-seed2-evaluation-order-correction-20260923-v2.json`。准备脚本首次缺PYTHONPATH在任何变更之前失败，随后显式配置执行成功。
- 当前下载spec `reset-range-seed2-local-evaluations-20260923-v2-spec.json`；终审spec `reset-seed2-finalization-20260923-v3-spec.json`，源pin `reset-seed2-finalization-20260923-v3`，SHA `506f9f13b20d65afa775ec6bd0e7b5240e519c54a25926fac668fed27a6fa03a`。最终自动下载训练日志/门禁，核查预算+CP，分析/打包/上传；未齐不得挑峰值。参数化训练审计已在首seed完整材料上回归通过，未重跑物理。

### 新归一化配对：冻结还是更新输入统计

- seed20261129，两臂都是2x重置；同原teacher/normalizer、新Adam、LR1e-5、5120×32×100。唯一干预：input normalizer冻结/更新。actor、critic、价值统计继续学习；不改奖励/动作/物性。
- run `wuji_bridge3_reset2x_norm{frozen,adaptive}_seed20261129_v1`；spec `reset-normalizer-pair-20260923-v1-spec.json`；suite `wuji_reset_normalizer_pair_20260923_v1_suite.json`；pin archiveSHA `ad03ffc10e35e0b1f9d91636b5c310982a7edbc447f678db03900612673d5c7a`。
- 本机/远端3单测通过，证据 `reset-normalizer-code-validation-20260923-v1/report.json`。frozen实际10000转移门禁及3轮PPO预检均过，统计逐元素相等且count73728001不变，actor/critic/value更新有限；预检KL .02061/.03219/.02055，正式100轮已开始。KL仍为SAPG聚合值，不当作同策略KL。
- **当前评估在八卡GPU0**，queue `reset-normalizer-evaluation-20260923-h100-v3-queue.json`，spec `reset-normalizer-evaluations-eight-20260923-v3-spec.json`；sourceSHA `eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09`。全部44条件统一同GPU/batch332/seed20261125，重测基线，不能与本机332或机制seed20261127直接混用。
- 原本机712869/712870于0评估/0审计取消，以减少反馈排队。H100v2只准备未启动；v3明确写入H100评分协议标签。原attempts和源码均保留。归一化完整终审879498已接上：spec `reset-normalizer-finalization-20260923-v3-spec.json`，sourceSHA `4125cc9765fc6b8dd21e12bdc10a61bea21939fb75119356d44b4a764d050af3`。等H10044完整审计后回传trace/CP并核验SHA，核查两臂预算与每个冻结统计CP，分析/打包/上传新Release。它显式打包真正H100评分源码，不能使用旧local评分器；旧v1/v2均在0审计/0打包的等待阶段取消。

## 已完成的关键结果

### 第一seed配对续训：两臂100完成，44评估完成

本机GPU/batch332/seed20261125，分母300，第四抓姿0/32。全部32,768,000正式训练转移及8,764,800评估转移独立审计；每臂另有491520预检与10000门禁。

|模型|小扰动2s/5s|宽扰动2s/5s|宽扰动刀身稳定2s/5s|
|---|---|---|---|
|原teacher|298/299|252/263|258/264|
|1x最终CP100|282/282|242/252|259/274|
|2x最终CP100|294/298|262/279|274/284|

2x在五个CP的宽扰动快慢均高于同预算1x，但仅单训练seed；无候选同时通过两时钟95%门槛。CP25→50快速退化主要是刀身稳定时端点偏离增多，不只是掉落。证据 `reset-range-cp-audit-monitor-20260923-v2/audit-44-20260923T131828Z.json`、`reset-range-control-analysis-final44-20260923-v2`、`reset-range-training-final-audit-20260923-v2.json`。全CP曲线已查看。

**Release43/43资产全部digest核验**，`release-reset-range-pair-complete-20260923-verified.json`；原终审432601完成。包含全部11个冻结权重、原始轨迹、日志和固定源码。

### 冻结归一化/持握机制：22阶段全完成

同四卡H100GPU2/batch332/seed20261127，6个门禁+16正式条件，3,198,000转移全量独立复算，正常退出，no-op的全部10个trace数组与native逐元素相同。证据 `reset-mechanism-gpu2-audit-monitor-20260923-v3/audit-22-20260923T134059Z.json`；原始trace已完整回传到本机 `reset-mechanism-gpu2-20260923-v3`。

原teacher快/慢261/267；CP100原生258/278，换原输入统计266/282；原权重换CP100统计229/258。CP50原生252/280，换原统计262/279。固定初始目标0任务成功、278/300身体稳定，0.5秒280稳定。

原权重换CP100统计快速净损32/300（修复10、损失42），描述性配对区间-15.0至-6.33个百分点。CP50/100换原统计的改善区间均跨0；慢速CP50还-1。故统计变化确实会改变控制，**未证明换回统计可解决退化**。固定持握失败也不是机械不可行证明，动态策略可以救回部分行。

离线分析 `reset-mechanism-analysis-complete-20260923-v2`；v1图例遮数字保留，v2移动图例，统计逐项相同且图已查看。分析pin `reset-mechanism-analysis-20260923-v2`。解释 `research/reset-normalizer-mechanism-20260923.md`。11个命名小型结果附件改上传新Release，最终核验 `release-reset-mechanism-complete-20260923-v2-verified.json`；其中不包含trace本体，raw仍在上述本机/共享远端。

### 原已冻结RGB/传感器结果与边界

- 冻结混合RGB，新独立小扰动300初态：287/300快速、294/300慢速；通过当时95%总体/每组90%工作门槛，仅三个已训练抓姿的新扰动。原RGB267/288。证据 `rgb-independent-final-rescored-1802-v1.json`、`research/wuji-rgb-independent-result-20260923.md`。
- 同RGB更宽300初态237/255；oracle真实当前物体teacher258/266、因果真值253/263（**旧4×83协议**）。此宽集已成为开发数据，不再是未见验收集。
- 实际自主sensor运行时旧开发332：288/295，旧第四0/32，CPU接口审计通过。CoreUltra7 CPU模型计时p50 4.69ms/p95 5.83/p99 6.35，不含相机/通信/电机，不是CPU闭环或真机结果。
- 当前RGB/runtime绑定**原teacherSHA**，不能伪造元数据替换新teacher。原teacher `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`；混合RGB `9221141fe68ec6c116d0b30fab1415794a0eefa48b4c0e8591ba7afe00669d28`。
- 宽集 `rgb-wider300-total-seed20261123-v2/mixed332.npy` SHA `ecb5989f1739a346f4fed5f174a98261737a069d94bff45a753538466168e025`；独立小集SHA `d04d8a2759533bb50b5ef49802acd8144db0f8924ed3723eef618fae23815e0c`。第四抓姿持续0/32，未见几何/广泛抓姿/真机尚未成功。
- 刀147×19×11mm、35g、50mm行程/40mm目标；Wuji20DoF，支持指±.04rad，拇指±.025rad/step，阻尼.3未实物标定。20s、30Hz控制/120Hz物理，外部2s/5s指令，最后9帧误差<2mm，刀身全程<10mm/.25rad，存活有效。
- Sharpa论文22DoF、功能抓姿/人工放置、特权teacher与50帧TCN、10mm到位指标。RGB迁移、Wuji手型/尺寸/控制及更严验收均须单列。既有失败与文献 `research/sharpa-success-and-wuji-student-gap-20260922.md`，不重复盲目纯本体感觉MSE或延长训练。

## 文档、源码与下一步

文档镜像760633每5分钟稳定读取字节、rsync远端并回读SHA；spec `handoff-mirror-20260923-v2-spec.json`，脚本SHA `e70ae2181a04c11fe90114a3537122cdc848d9c3b99f817b6fd61d8bdf8a9067`。每周期读取注册表的`local_runs`，**远端拥有的状态不能放进local_runs**。不覆盖远端训练/调度状态。

最近全局源码220509：`source-history/source-snapshot-20260923T220509.tar.gz`，SHA `23e0e08cbd8b1d67115ca656272ba95eb932a11f068f1d3ff920872a8a7826dc`；源码同步完成，archive和manifest远端SHA回读一致，证据 `source-history/source-snapshot-20260923T220509-remote-verified.json`。文档实时状态以每5分钟镜像为准。源码同步使用 `runs/wuji-goal/source-sync-files.txt`，排除监控配置/运行status；pin的runs软链接不可展开。

当前发布入口：https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923 （ID394720794）。原Release https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921 （ID392488331）已经达到附件上限；所有原资料保留。GitHub422明确返回 `file_count limited to 1000 assets per release`，证据 `release-reset-mechanism-upload-diagnostic-20260923-v2/diagnostic.json`。机制v1上传4项已验哈希后停止，其余重传新Release组成完整11项，README指向原权重Release。新Release与原合集指向同一基础commit313ba8ea，实验真实源码以附件pin哈希为准。创建请求/响应 `release-continuation-20260923-v1`。

两自动终审已分别升级v3，显式指定新release_id；旧等待进程809499/847614取消，0物理/0审计/0打包被中断。不要重启旧硬编码原Release的上传器；新上传器支持--release-id并保留HTTP错误体。

下一步：809497已开始1xCP，已审CP10小快/慢293/300、宽251/279（各/300），都为早期开发数；64822已取得八卡GPU0并执行全部四基线，新同机小快为294/300；核验归一化CP统计持续冻结；收齐第二seed与归一化所有CP的配对结果，区分身体与端点再选改进。两套完整终审已启动；确认机制新Release11资产发布；完成本轮源快照和文档回读。任何候选调参结束后冻结，再生成**新独立行**验收；当前开发行不能重新叫独立。新teacher须重新验证与RGB兼容。目标仍未完成。

## 14:11 UTC 实查补记

两参考seed2已500/500完成；helper44720于14:05:54正常完成，八卡新CP scheduler71673，池[0,2,1,3,4,5]，五张释放卡正在做有用CP评估。归一化基线四项全部独立复算，小294/298、宽261/267（各/300），随后normfrozenCP10开始；不可混用本机基线。两自动终审879492/879498仍活跃等待全部44。机制11附件已全digest核验。原训练88339实查仍运行。

新增待检验假设：训练object终止位姿阈值是.05m/1.57rad，验收全程阈值.01m/.25rad；绝对位姿惩罚已存在，并非完全无惩罚。先离线量化旧44轨迹的严格失败后仍有效时长、重获稳定和端点情况。评估轨迹不含实际训练奖励，不把可能奖励机会当实际回报；尚未更改终止、奖励或运行pin。

## 新实验：训练终止条件配对 2026-09-23T14:20:59.663776+00:00

首seed全部44旧轨迹离线分析完成（0新增物理），`research/termination-objective-gap-20260923.md`和`diagnostics/termination-gap-analysis-20260923-v1`。2xCP100宽快速26次严格刀身失败中20次重获9帧稳定；原生存活292、严格刀身274、完整成功262/300。实际越界时长中位0.1s，不能声称多数失败后长期拿奖励。

新增仅比较训练native(.05m/1.57rad)和strict(.01m/.25rad)，同原teacher/normalizer、新Adam、归一化正常更新、seed20261130、2xreset、每臂5120×32×100。完整奖励/动作/物理和评估原生终止均保持；评估继续用严格离线指标。训练spec`termination-pair-20260923-v1-spec.json`，suite`wuji_termination_pair_20260923_v1_suite.json`。source pin：`/home/wangjiarui/artgym-pinned-termination-pair-20260923-v1`，SHA`0ccd340eb4353011a4e9562bd8cf7aec87a0e4fc8da7486965de0236e4486400`；本机及远端已核验3673文件，配置合成仅两个终止值不同。

四卡GPU1训练协调器 **290813**，八卡GPU1评估 **75115**、五分钟评分 **75116**，本机终审 **974473**。均用内核独占租约等待既有worker结束，不取消已有任务。协调器`diagnostics/termination-pair-20260923-v1`，eval`termination-evaluations-eight-20260923-v1`，audit`termination-cp-audit-monitor-eight-20260923-v1`，finalizer`termination-finalization-20260923-v1`。终审完成44后回传证据、核查预算/配置、打包发布新Release394720794。

两臂先实际10000步门禁核对终止mask再3轮PPO预检，随后正式从原权重开始。评估全部44重新同八卡GPU1/batch332/seed20261125建立基线，nativeCPs在先、strictCPs在后；不能混用其他GPU基线。门禁/训练尚待真实结果，不把已排队称作开始学习。旧本机配置检查v1在IsaacGym导入阶段非零退出，原因未定、无物理；v2同配置成功，旧失败保留。

第二扰动seed两臂100均已完成，44评分继续。归一化frozen全部五个CP统计逐元素等于原值、count73728001，证据`diagnostics/normalizer-frozen-allcp-statistics-20260923-v1.json`（远端需回传）；adaptive尚运行。以上新任务已经注册到5分钟health和文档镜像。

## 终审环境修复 2026-09-23T14:25:57.633414+00:00

发现运行时LD_LIBRARY_PATH使系统SSH链接到conda OpenSSL3.6，而SSH基于3.0，实际远端读取返回255。旧归一化/终止终审只有重试心跳、尚未读取成功；第二seed终审尚等本机44，后续同步也会受影响。已用原污染环境复现，并以清理后的环境真实检查SSH到八卡、Release394720794读取、rsync/curl版本，全部通过。只对外部SSH/rsync/curl/gh清理LD并优先系统PATH，Python/仿真runtime保留。2单测通过。

- reset-seed2-finalization：旧879492在0审计/0打包且无子进程时取消；新 **1000149**，`runs/wuji-goal/reset-seed2-finalization-20260923-v4-spec.json`，sourceSHA`70c873461e1a00f457dfb43fc8f817054d68c7fcc2b91aa86b3e1be2a40e57ff`。
- reset-normalizer-finalization：旧879498在0审计/0打包且无子进程时取消；新 **1000151**，`runs/wuji-goal/reset-normalizer-finalization-20260923-v4-spec.json`，sourceSHA`101327978af15c0041ee53060136cc2678f0b4b17d732405eb7ac833f312955a`。
- termination-finalization：旧974473在0审计/0打包且无子进程时取消；新 **1000171**，`runs/wuji-goal/termination-finalization-20260923-v2-spec.json`，sourceSHA`3a81a80666167dc00c05a7026e51efea1bb42dc0763e9d7d910d60622ff8cb5d`。

所有训练/评估进程均未中断。新终审也带齐两层支持release-id的上传器；旧waiting和错误记录保留。以上ID取代先前表中终审ID，registry已更新，镜像将自动跟进。
