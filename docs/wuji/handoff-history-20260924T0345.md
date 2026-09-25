# Wuji 美工刀持续实验：接续入口

更新时间：2026-09-23T15:09:19.829550+00:00。23:08最新核验优先于下文历史补记，见 research/teacher-progress-20260923T2308.md；之前版本存 research/handoff-history-20260923T2308.md。

## 最新核验：2026-09-23 23:08 CST

第二seed两臂100和44评估全完成。2x最终CP100小扰动300/300、300/300；宽265/300、278/300；第四0/32。全部是已观察开发集，无CP同时过宽两时钟95%，未达总体目标。详见 `research/teacher-progress-20260923T2308.md` 与 `diagnostics/teacher-status-20260923T2308-summary.json`。

第二seed下载809497/评分809498已完成，终审1000149在publish阶段。归一化两臂100完成，八卡64822完成41/44物理、64823重评分40/44；最终adaptive100待齐。native终止100完成，strict门禁10000/预检3轮通过、正式CP25，四卡teacher294373；八卡75115完成19/44物理、75116重评分17/44。原训练88339本轮直接实查存活。4hGPU约59%/59%，五分钟巡检及文档镜像继续。下文更早的pending/CP10记录是历史状态。

## 先读与约束

1. 实验根 `/data/research/artgym-experiments-20260921`，非Git；原仓库 `/data/research/artgym` 保留。本文件在两根目录和共享远端有镜像。
2. 再读 `runs/wuji-goal/goal-state.json`、`runs/wuji-goal/health/LATEST.md`、`runs/wuji-goal/journal/events.jsonl`。下文短路径默认在 `runs/wuji-goal/`。
3. **不创建子代理。保留本机原训练88339。** 不改在途源码pin；失败/取消保留，新尝试用新目录。IsaacGym先于torch；GPU子进程用 `runtime_environment` 与本机 `/tmp` 独占GPU租约。
4. 用户授权持续研究、训练、修复及向 **Jr-kelly/artgym** 发布命名可视化；视频无文字。仅有用计算，平台GPU四小时均值门槛26%，目标>40%。不能将脚本/训练内/旧开发集/特权真值说成独立或硬件成功。
5. Goal工具仍外部blocked，无可调用resume接口，客户端命令 `/goal resume`。授权工作实际继续；未达目标不标complete。

## 机器与运行环境

**.106:30147和.93:30147是同一八H100机器两入口**，不是16卡。hostname `d-20260921021501-6zzgt`。四卡.73:30296 hostname `d-20260920124121-d9ns7`。两机共享GPFS文件、PID命名空间不同，远端无rg。

```bash
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.106
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.93
ssh -p 30296 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.73
```

远端根 `/home/wangjiarui/artgym-experiments-20260921`；Python `/home/wangjiarui/artgym-runtime/bin/python`。本机Python `/home/agiuser/miniconda3/envs/artgym/bin/python`。模块cwd/PYTHONPATH须指向pin及pin/rl_games，避免editable原仓库。CPU unittest用discover避免tests包冲突。

**新增已验证环境修复**：Python runtime的LD_LIBRARY_PATH会令系统SSH加载错误OpenSSL（built3.0、loaded3.6，退出255）。`scripts/host_tool_environment.py`只为SSH/rsync/curl/gh移除LD_LIBRARY_PATH/LD_PRELOAD并优先系统PATH，仍保留用户gh路径。Python/物理运行环境不变。2单测、污染环境下真实远端hostname和Release394720794读取通过。三个旧终审在0审计/0打包且无子进程时取消，训练/评估未中断；不要重启旧终审。证据 `diagnostics/host-tool-finalizers-{validation,launch}-20260923-v1`（launch为.json）。

## 当前任务

|主机|任务|PID|状态/入口（diagnostics下）|
|---|---|---:|---|
|本机|原训练|88339|保持，本轮已实查|
|本机|五分钟健康巡检|3132243|注册表goal_health_monitor.json|
|本机|五分钟文档镜像v2|760633|handoff-mirror-20260923-v2|
|本机|第二seed CP下载+物理评估|809497|reset-range-seed2-local-evaluations-20260923-v2|
|本机|第二seed五分钟独立评分|809498|reset-range-seed2-cp-audit-monitor-20260923-v3/LATEST.md|
|本机|第二seed完整终审v4|1000149|reset-seed2-finalization-20260923-v4，等44|
|八卡GPU0|归一化CP评估v3|64822|reset-normalizer-evaluations-eight-20260923-v3|
|八卡|归一化五分钟评分|64823|reset-normalizer-cp-audit-monitor-eight-20260923-v3/LATEST.md|
|本机|归一化完整终审v4|1000151|reset-normalizer-finalization-20260923-v4，远端读取恢复|
|四卡GPU1|新终止阈值配对|290813|termination-pair-20260923-v1，native实际门禁/预检通过，正式CP10，teacher292518|
|八卡GPU1|终止阈值CP评估|75115|termination-evaluations-eight-20260923-v1，已获得GPU1，基线/CP实际执行|
|八卡|终止阈值五分钟评分|75116|termination-cp-audit-monitor-eight-20260923-v1|
|本机|终止阈值完整终审v2|1000171|termination-finalization-20260923-v2，远端读取正常|

第二seed训练284122已两臂100/100正常完成；归一化训练286696已两臂100/100正常完成（14:23:10）。各配对32,768,000正式转移，两份完整训练审计已回传本机：`reset-seed2-training-completed-early-audit-20260923-v1.json`、`reset-normalizer-training-completed-early-audit-20260923-v1.json`（均在diagnostics）。终审将另做完整训练+评估+发布审计，输出名不同不冲突。

### 资源及参考实验

四卡Sharpa corrected：launcher106419、GPU0/3、最近CP5400/6250；CPscheduler287262、池[2,1]。八卡原Sharpa upstream：GPU6/7、最近CP4150+ /6250；第二seed upstream22713和corrected22714均500完成。helper44720于14:05:54完成，八卡CPscheduler已改为 **71673，池[0,2,1,3,4,5]**；新Wuji任务按租约等待，不取消既有worker。

14:24健康：四卡4h56.60%、5min64.45%；八卡见LATEST，均无告警。26%平台口径与本机采样区别保留。物理评估一项CP含多几何，持有租约直到完整worker结束，不能只看到新任务等待就认定GPU空闲。

## 三组续训定义与最新解释

共同原teacher SHA `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。每臂从该权重及原输入统计开始、新Adam、LR1e-5、5120×32×100=16,384,000正式转移；另10000实际转移门禁+3轮491520转移PPO预检，正式重新从原权重开始。只采样三个原始训练抓姿在线扰动，绝不采样评估行。

1. **第二扰动seed20261128**：1x再2x。1x为位置分量±0.5mm/关节±.01rad/旋转向量分量±0.5度；2x翻倍。run `wuji_bridge3_reset{1,2}x_cp25_seed20261128_v1`。训练spec `reset-range-seed2-20260923-v2-spec.json`，sourceSHA `ff94128c8c14782b86c804c62dd169187ae57c2abdef4e5a2b02a67e14637088`。评估queue `reset-range-seed2-evaluation-20260923-local-v2-queue.json`：仅改未开始CP顺序，条件名仍-local-v1，4个原基线逐字节复用；旧错误等2x队列0物理取消，证据order-correction-v2。1x最终小283/290、宽237/257（/300，2s/5s）；2x待完整评分。不得只挑峰值。
2. **输入统计seed20261129**：两臂都2x，仅冻结/更新input normalizer；actor/critic/value统计训练。run `wuji_bridge3_reset2x_norm{frozen,adaptive}_seed20261129_v1`。spec `reset-normalizer-pair-20260923-v1-spec.json`，训练sourceSHA `ad03ffc10e35e0b1f9d91636b5c310982a7edbc447f678db03900612673d5c7a`。两臂100完成。frozen五个CP输入统计逐元素等于原值、count73728001；adaptive最终count93388801，权重/价值统计均更新且有限。证据 `diagnostics/normalizer-frozen-allcp-statistics-20260923-v1.json`。八卡GPU0/batch332/seed20261125重测全四基线：小294/298、宽261/267。frozenCP10宽270/281，CP25宽261/281，CP50宽254/274；冻结统计仍不能消除阶段性退化，完整配对待齐。评估sourceSHA `eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09`。
3. **新终止阈值seed20261130**：两臂2x、归一化正常更新，仅训练终止native(.05m/1.57rad)对strict(.01m/.25rad)。奖励/绝对位姿惩罚/动作/物理保持。run `wuji_bridge3_reset2x_done{native,strict}_seed20261130_v1`；spec `termination-pair-20260923-v1-spec.json`，suite `wuji_termination_pair_20260923_v1_suite.json`，sourceSHA `0ccd340eb4353011a4e9562bd8cf7aec87a0e4fc8da7486965de0236e4486400`。3673源文件本机/远端验证，真实Hydra合成仅两个终止阈值不同；本机配置v1导入阶段非零、原因未定、0物理，v2和远端v1成功，失败保留。native实际10000步门禁（125次动作映射、终止mask0不一致）和3轮PPO预检通过，正式CP10已出，strict臂仍按先后顺序等待。八卡GPU1评估所有模型仍用原生终止，然后同一严格规则离线评分，不能用改评估环境制造提升；重新测四基线，44条件统一GPU1。原>终止与验收<的等号差异已记录。

三组全部评估原baseline+两臂CP10/25/50/75/100，各小/宽开发扰动、2s/5s，共44。每条件600×332，前三组各100、第四32保留。任何本机/H100/4×83/不同seed协议不直接混用。固定最终CP和全曲线都保留。

### 新终审版本与源码

- 第二seed `reset-seed2-finalization-20260923-v4-spec.json`，sourceSHA `70c873461e1a00f457dfb43fc8f817054d68c7fcc2b91aa86b3e1be2a40e57ff`。
- 归一化 `reset-normalizer-finalization-20260923-v4-spec.json`，sourceSHA `101327978af15c0041ee53060136cc2678f0b4b17d732405eb7ac833f312955a`。
- 终止 `termination-finalization-20260923-v2-spec.json`，sourceSHA `3a81a80666167dc00c05a7026e51efea1bb42dc0763e9d7d910d60622ff8cb5d`。

终审等44齐，回传trace/CP/日志/门禁，核验哈希与预算，分析全曲线，打包并上传**新Release394720794**。实际H100评分器源码随包；不是旧local评分器。旧879492/879498/974473已在等待0审计/0打包且无子进程时取消，记录保留。新终审已真实读到远端monitoring且无OpenSSL错误。

## 已完成关键证据

### 第一扰动seed20261124：两臂100、44全量评估

|模型|小2s/5s|宽2s/5s|宽刀身稳定2s/5s|
|---|---|---|---|
|原teacher|298/299|252/263|258/264|
|1x最终100|282/282|242/252|259/274|
|2x最终100|294/298|262/279|274/284|

各/300，第四0/32。32,768,000训练+8,764,800评估转移全量审计。2x每个预定CP的宽快/慢均高于1x，但只有此单seed时不推泛化。无候选同时过95%两时钟门槛。`diagnostics/reset-range-cp-audit-monitor-20260923-v2/audit-44-20260923T131828Z.json`、`reset-range-control-analysis-final44-20260923-v2`。43/43附件在原Release全部digest核验，包括11权重/全部trace/日志/pin。

### 冻结归一化/持握机制：22阶段完成

同四卡H100GPU2/batch332/seed20261127，6门禁+16正式，3,198,000转移，全正常退出+逐条评分。No-op与native两时钟全部10个trace数组完全相等。原teacher261/267；CP100原生258/278、换原统计266/282；原权重换CP100统计229/258；CP50原生252/280、换原统计262/279。固定初始目标任务0/0，但刀身278/300稳定（.5s时280）。动态策略能救回部分固定持握失败，因此后者不是机械不可行证明。

原权重换CP100统计快损32（修复10、退化42），描述性配对区间-15.0至-6.33pp。CP50/100换原统计改善区间跨0；不能宣称统计是唯一原因或换回即解决。`research/reset-normalizer-mechanism-20260923.md`、`diagnostics/reset-mechanism-analysis-complete-20260923-v2`；原始trace在`reset-mechanism-gpu2-20260923-v3`已回传。**新Release11/11小型附件digest已验证**；附件不含raw trace本体，原权重/trace另有完整包。

### 终止目标离线诊断：44原轨迹、0新增物理

2x最终快速：原生存活292、严格刀身274、完整成功262/300。26次严格刀身失败中20次重获至少9帧稳定，实际界外时长中位.1s。故不能说多数长期掉落后赚奖励；有短暂越界后恢复，也有稳定刀身但端点不达标。评估关闭到位奖励，此处近目标时间不是实际训练回报。严格终止是否改善学习必须看新配对，也可能妨碍恢复探索。

`research/termination-objective-gap-20260923.md`、`diagnostics/termination-gap-analysis-20260923-v1`；分析pinSHA `4d699aa0863db870a11569945437ca76c856f35dea40bf7a95e18b1ea4f62cdd`。图已查看，`termination-gap-plot-20260923-v1/failure-categories.png`；新Release **5/5附件digest验证**，`release-termination-gap-20260923-v1-verified.json`。图与分析是原44诊断，不能当新终止训练结果。

## 已有独立RGB结果与边界

冻结混合RGB在冻结后生成的新小扰动300初态：287/300快、294/300慢，通过当时总体95%/每组90%工作门槛；只三个已训练抓姿的新扰动。证据 `rgb-independent-final-rescored-1802-v1.json`、`research/wuji-rgb-independent-result-20260923.md`。更宽300后来变为开发集，RGB237/255、oracle真实teacher258/266、因果真值253/263（这些为**旧4×83协议**）。第四抓姿始终0/32，不能称作广泛抓姿/未见几何/真机成功。

实际自主sensor旧开发332：288/295，CPU接口审计通过；CPU模型p50 4.69ms/p95 5.83/p99 6.35，不含相机/通信/电机，不是CPU物理闭环或硬件结果。RGB/runtime仍绑定原teacher，不能更换teacher并伪造元数据。混合RGB SHA `9221141fe68ec6c116d0b30fab1415794a0eefa48b4c0e8591ba7afe00669d28`；宽集SHA `ecb5989f1739a346f4fed5f174a98261737a069d94bff45a753538466168e025`。

现实刀147×19×11mm、35g、50mm行程/40mm目标。Wuji20DoF，支持指±.04rad、拇指±.025rad/步，阻尼.3未实物标定。统一严格20s、30Hz控制/120Hz物理，外部2s/5s指令，末9帧<2mm，刀身全程<10mm/.25rad且有效存活。

Sharpa论文22DoF、功能抓姿/人工放置、当前物体特权teacher、50帧TCN、10mm到位；不含自主取刀。当前upstream/corrected参考与明确paper公式失败分支有差异，不能统称完全对齐。文献与既有失败 `research/sharpa-success-and-wuji-student-gap-20260922.md`。SAPG聚合KL含跨探索组差异，不是同策略更新距离；旧零LR诊断同策略精确KL=0但聚合约.15-.31。现续训预检原聚合阈值不当作精确KL证据。

## 发布、备份和下一步

新Release：https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923 （ID394720794）。原：https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921 （ID392488331），已经1000附件上限。原附件全保留，GitHub422证据`release-reset-mechanism-upload-diagnostic-20260923-v2/diagnostic.json`。新Release仍同基础commit313ba8ea，真实实验源码以附件pin为准。不要使用硬编码旧ID的上传器。

最近全局source snapshot224423 SHA `00832458e7bd71c73a43abf0ce605a4e7a2a9bc8b99fb82264483538179cdf53`；source-sync-files同步完成，本次archive与manifest远端回读SHA一致；前一批16个附属artifact的回读记录保留在222802验证文件。本次证据`source-history/source-snapshot-20260923T224423-remote-verified.json`。快照早于此即时文档属于正常版本差异。

镜像760633每5分钟读取稳定字节、同步并回读SHA，动态跟随registry.local_runs；远端拥有的状态不能加入local_runs。镜像spec`handoff-mirror-20260923-v2-spec.json`；sourceSHA `e70ae2181a04c11fe90114a3537122cdc848d9c3b99f817b6fd61d8bdf8a9067`。source同步不要覆盖监控配置和remote status，不展开pin/runs链接。

下一步按优先序：

1. 继续检查新终止native正式训练；它完成后strict臂须实际10000转移门禁/3轮PPO预检再正式。75115已在八卡GPU1按44队列评估。失败保留，不改在途pin。
2. 等第二seed和归一化全44评分，核查新终审1000149/1000151读取正常、按新Release发布；终止终审1000171同理。
3. 读全CP、身体/端点分解与配对差异；不从一个CP峰值宣布成功。归一化CP50已有退化，冻结统计单独不足。
4. 候选调参结束后冻结，重新生成**新独立行**验收；已观察宽集不能再称盲测。新teacher还要重新验证/训练RGB兼容。更广抓姿、未见几何和硬件未完成。

## 离线补充：初态与策略互补 2026-09-23T14:40:29.685251+00:00

`research/early-failure-policy-coverage-20260923.md`：16个机制条件全部重新核验，八种控制器共同前.5s失败的开发行仅0/4/87；四个学习权重的事后成功并集快289/慢293，同一权重两时钟成功覆盖288/300。是事后标签并集，**不是可部署策略或独立成功**；没有训练/选择新模型，没有删除失败初态。此结果只为后续策略保留/选择研究提供线索，先收齐现有配对。0新增物理。

## 最新训练/评分补记 2026-09-23T14:44:23.247659+00:00

native终止臂CP10 SHA`ded1cd09c1d0d8dc4464289538f7a0ca49fb4b060131d81eea4ac88273f8af84`；门禁实际10000判定，原生fall4个元素、严格身体越界143个元素、mask不一致0。3轮预检输入统计73728001→74317825、actor/critic/value更新且有限；聚合KL .03542/.01580/.02159，不当精确同策略KL。证据`diagnostics/termination-native-early-training-check-20260923-v1.json`。strict尚未开始，不宣称已通过。

归一化冻结组最终100已评：小278/289、宽243/261（/300）。相较同H100基线294/298、261/267退化，尤其宽B组57/73；全部五CP统计实际冻结，因此输入统计改变不是必要退化条件。adaptive完整结果待齐，不提前认定最终优劣。当前4hGPU四卡57.89%、八卡56.73%，无告警。106/93本轮重新对照hostname/boot/全部8个GPU UUID完全相同，证据`diagnostics/host-alias-reverified-20260923-v1.json`。

官方Goal恢复命令已于2026-09-23T14:46:20.357473+00:00重新读取确认：https://learn.chatgpt.com/docs/developer-commands?surface=cli ，`/goal resume`。工具仍返回blocked且此会话无resume工具，后台训练/巡检/评估正常进行；不虚报工具状态已恢复。


## 自动更新：第二训练seed完整审计 2026-09-23T15:29:04.530182+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/reset-range-seed2-control-analysis-final44-20260923-v1`；发布核验 `runs/wuji-goal/diagnostics/release-reset-range-seed2-complete-20260923-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：输入归一化配对完整审计 2026-09-23T15:46:48.453073+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/reset-normalizer-control-analysis-final44-20260923-v1`；发布核验 `runs/wuji-goal/diagnostics/release-reset-normalizer-pair-complete-20260923-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 论文对齐复核 2026-09-24 00:16 CST

最新对照表 `research/paper-alignment-current-20260924.md`，source哈希 `diagnostics/paper-alignment-current-20260924-evidence.json`。当前成功teacher属于Wuji迁移，**未严格对齐**奖励/控制/物性随机化/数据规模/预算/评估。Sharpa公式分支仍数值失败，upstream/corrected不是公式相同。归一化与终止各44评估已完整；终止strict最终300/300小、279/283宽，第四0/32。终止打包v2缺package_wuji_dagger_final，失败保留、新pin修复。00:10八卡短期利用率低告警（5min21.76%，4h60%），需要补充有用计算。上文23:08 pending已过时。


00:18续接：补充四项有用的Sharpa匹配预算评估，upstream/corrected各CP3000/4000，五个未见几何全部有效抓姿各100次随机rollout。它只把该项重复数补齐，不能称完整论文公式复现或新的盲测。八卡GPU1/3/4/5，PID105768/105769/105770/105771；00:19已实查四个物理子进程105784/105781/105782/105783均在030运行，四卡GPU采样95%/97%/95%/96%。旧参考训练及CP监控保留。固定源码复用reset-normalizer-evaluations-eight-v3（archive SHA eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09），新增driver SHA ee4166ee86185c91ed58a5c9d42699776c4bdd3b32af99509ef6cdb51ad72f3c。配置、源checkpoint哈希、进程见 diagnostics/sharpa-matched100-20260924-v1/{spec,launch}.json。使用/tmp独占GPU租约，已加入五分钟健康注册；接下来收集四结果和逐项重算IC/GC/CSC，不把CPU包装故障误作训练失败。
