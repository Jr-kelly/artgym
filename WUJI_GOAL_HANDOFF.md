
## 2026-09-25T15:18:20.908356+00:00 修正路线当前收尾

先读research/g2-air-flip-results-20260925.md。用户滑块朝下→取刀→小臂手整体180°翻掌已验证V2；后续V4开环和V5腕真值跟随均在手内调整失败，无新teacher/student操作。V5第704帧因52.1mm刀身偏移中止；4个物理进程已结束。下一项仅建议固定翻掌前缀、分指迁移的有界方案，未执行；无新训练，原88339保留。旧端立不再符合用户现实路线。即将新增Release只备份本轮4项和诊断；旧v6/v7不覆盖。

## 2026-09-25T15:15:42.797914+00:00 空中换握第一物理对照失败

V4前690帧与滑块朝下V2取刀/翻掌逐元素一致，后续12秒换握期间渐进转偏：第8秒0.329rad，第10秒0.663rad，第11.96秒1.317rad/28.5mm，滑块被动打开；在转运初段落桌，operation_steps=0。不要归因唯一为末段减压：减压之前已经转偏。完整42秒失败保留。

V5仅改 --seat-feedback object-truth，手指/物性/源码pin与V4相同（清单SHA5d1c7232…），使用既有5mm/0.05rad限速IK及50mm/0.8rad刀身范围；仍是理想定位对照。PID556357，结果待收。代码已推GitHub d4b68d8；origin是本机备份仓库，外部推送需从/home/agiuser/artgym-full-backup-20260925-v1/code-branch完成，主工作树HTTPS helper读取.git/config报权限错误，已用备份中转推送成功。

## 2026-09-25T15:08:45.606731+00:00 滑块朝下取刀翻掌通过；手内调整在途

B-sliderdown-pronate180-h30-v2完成25秒，750帧，无操作：滑块面朝上分量-0.9993→+0.9850，掌心-0.8043→+0.8044，实际翻179.821°；翻转期间刀手相对最大平移3.941mm、转角0.1556rad，无失联或落桌。完整末秒保持通过。手/刀物性同v1字节一致，臂关节位置与指令/实测速度无超限。预览http://127.0.0.1:8767/g2-sliderdown-pickup-flip180-v2.mp4。

从v2实际flip末态推导手内规划，不用它重设状态。单求解路径v3接触误差15.47mm被几何筛除，未做物理。v4加入功能角度种子比较，接触误差0.149mm、臂位置残差0.60微米；实际12秒换握正在B-sliderdown-airseat-teacher-v4 PID530855中验证。任何成功需读report/trace，不把几何路径当物理。原88339保留、无新训练。

## 2026-09-25T15:04:52.018916+00:00 用户补充初始滑块面朝下

当前正确路线：初始滑块朝下、掌心朝下侧夹→小臂与手整体翻180°→滑块和掌心朝上→手内调整→冻结伸缩。上一个v1滑块初始朝上仅为翻掌控制对照：750帧/25秒，179.818°，相对位移0.657mm，未掉刀；不代表修正路线完成。新v2从滑块朝下正常摆放开始，考虑3mm突出滑块，初始刀心0.7571m后自由静置2秒，再一次仿真定位规划抓取。没有改变刀/桌物性、没有夹具或端立。B-sliderdown-pronate180-h30-v2 PID508742启动，结果待核。

## 空中翻掌新路线 2026-09-25T14:59:32.827724+00:00

用户否定端立换握的现实适用性。当前分支 feat/g2-wuji-air-flip-20260925，运行目录 runs/g2-air-flip-v1；先读 research/g2-air-flip-20260925.md。改为掌心朝下取刀→空中约180°翻掌→手内调整→冻结策略。旧v6/v7保留，不再代表新路线成功。先验证夹持翻掌，无新训练；原88339保留。
> 当前活动目标已转为 **G2＋Wuji 桌面取刀→冻结策略**，请先读 [G2_TABLETOP_HANDOFF.md](G2_TABLETOP_HANDOFF.md)。本文件的 complete 仅指9月24日预置持刀旧目标；新目标仍 active，B/C尚未接通。旧4090训练保留。本独立工作树维护新记录，不覆盖原仓库的旧成功版本。

## 新阶段：G2桌面取刀→伸缩（2026-09-25）

2026-09-25 22:13 CST：本轮固定仿真基线+20次验证及增量发布已交付。独立工程 `/data/research/artgym-g2-tabletop-20260925`，分支 `feat/g2-wuji-tabletop-20260925`；先读该工程 `G2_TABLETOP_HANDOFF.md` 和 `research/g2-tabletop-final-report.md`。固定A63/B65/C66两轮10mm/稳定通过，B/C未全过2mm；C仍是仿真定位/理想初始化。20次小变化全部结束，B/C各初抬10/10、到接管0/10、整段0/10，条件操作未评估。小变化泛化失败，真机未验证；不能用固定成功宣称这些已解决。

成功视频在 https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-fixed-abc-20260925-v6 ，最终验证/报告/代表失败在 https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-validation-20260925-v7 ，全部附件及20次归档内容已核验。旧driver已终态，不重启或替换失败。无新训练，原训练88339仍运行。下一轮只建议获取转腕时长5/10秒的6次有界对照，尚未执行；继续时新建记录并保留本轮冻结成果。


## 全量备份本机部分完成（2026-09-25T04:44:30.604777+00:00）

本机3目录192177文件/208190472088字节已完整捕获、全量恢复核验；225分卷及元数据已上传并逐项校验GitHub SHA256，Release https://github.com/Jr-kelly/artgym/releases/tag/wuji-full-backup-20260925-v1 。详细完成记录 `/home/agiuser/artgym-full-backup-20260925-v1/FINAL.json` 与 `runs/wuji-goal/diagnostics/full-backup-20260925-v1-final.json`。远端SSH全部拒绝连接，远端独有文件待补，不能称所有机器全量完成；用户新入口到达后先拉取远端差异继续备份。后续新增CP/日志亦需增量。备份README内含下载、恢复、路径迁移说明。


## 全量备份执行中（2026-09-25）

用户明确要求全量备份到GitHub。备份工作根 `/home/agiuser/artgym-full-backup-20260925-v1`，spec.json 固定三个本机目录：原仓库、实验副本、早期demo工作树，约195GiB/19万文件，包含隐藏文件、.git、所有原始CP/日志/轨迹/失败记录/缓存与项目tmp。内容按64MiB块SHA256去重，封装标准tar+zstd分卷；manifest恢复全部路径。原4090 PID88339仍在训练，保留进程，备份逐文件捕获+第二遍变化核对，活跃日志记录为时间前缀，非原子整盘快照。

远端 .106/.93:30147、.73:30296、.59:31973 本轮全部Connection refused；已向用户请求恢复入口或新SSH地址。远端独有文件待补，不能把本地完成称全部机器完成。GitHub新Release tag拟 `wuji-full-backup-20260925-v1`，先完成可恢复验证再发布；工具在工作根tools/，进度status.json。查实际进度后继续，勿覆盖已封装分卷或冻结源码。 已创建Release草稿396269037；代码分支backup/wuji-full-20260925已推送。进程记录分别在备份根snapshot-process.json、upload-process.json、finalization-process.json，实际PID需重查；finalize_local.py会全目录恢复、逐文件SHA校验、上传元数据并发布本地部分。最终以FINAL.json为准，远端未连通前all_hosts_complete仍false。


## GitHub发布覆盖核验（2026-09-25）

本轮回答“是否所有进展和尝试都上传”，做只读GitHub核验：3个Release分页共1330资产（3/1000/327）；核心teacher+student17/17文件SHA256再次通过。66个本地发布目录中65个顶层文件全部按名/大小匹配，另一个有plot-provenance.json无同名独立资产，未据此宣称内容漏传。GitHub仅main与9月20日早期demo分支，后续源码以Release压缩包发布。最新sim2real分析、接续/日志尚未上传，也没有全工作目录/全部中间CP备份证明。完整状态 `runs/wuji-goal/research/github-publication-status-20260925.md`；API及匹配证据 `diagnostics/github-publication-audit-20260925-v1/`。本轮没有发布或改训练，审计时间 2026-09-25T03:09:08.927142+00:00。用户后续路线应保留简化模型、优先真实标定+DR，精细CAD按实机证据决定。


## Sim2real 与实物建模咨询（2026-09-24）

已核对在线原文v1及当前发布权重配置，详见 `runs/wuji-goal/research/sim2real-assessment-20260924.md`；原文回执 `research/sim2real-paper-source-20260924.json`。当前成功策略固定质量/摩擦/阻尼、jointNoise=0，尚无Wuji实物标定；基本仿真Goal完成不代表sim2real完成。论文采用独立实物开环重放选择有效物性、参数随机化、student闭环蒸馏、真实物体简化孪生和top5筛抓姿。建议针对最终真实刀具优先建模接触形状与启动/滑动/卡位阻力，同时核验Wuji指腹与执行器响应，然后敏感性评估、按标定结果随机化续训和重新蒸馏。用户此轮是咨询；这些后续实验尚未启动，没有改冻结模型/Goal或发真机指令。本次报告与交接已保存两个本机入口；远端 .106/.93:30147、.73:30296 均连接失败，镜像待连通后补，证据 diagnostics/sim2real-assessment-mirror{,-fallback}-20260924.json。记录时间 2026-09-24T07:21:47.446207+00:00。


## 本地视频打开方式（2026-09-24）

用户反馈 Firefox 直接打开本机绝对路径显示找不到文件；已实查两个视频存在且可读，未判定浏览器失败根因。已启动仅绑定 127.0.0.1:8767 的本地 HTTP 服务，检查时间 2026-09-24T07:13:13.967146+00:00，PID 4098（接手需重新核验）。

- Teacher：`http://127.0.0.1:8767/teacher.mp4`
- Student：`http://127.0.0.1:8767/student.mp4`

上述 URL 均 HTTP 200、video/mp4，下载 SHA256 与发布视频源文件一致。服务目录 `runs/wuji-goal/local-video-preview-20260924`，仅有两个视频别名；证据 `runs/wuji-goal/diagnostics/local-video-preview-20260924.json`，日志同名前缀 `-server.log`。用户执行 `firefox http://127.0.0.1:8767/teacher.mp4` 或对应 student 地址即可。服务只在本机可用，机器重启后须按证据中的 command 重启。没有重新生成视频或改变训练/Goal 状态。


## 最新结论：基本 teacher + student Goal 完成（2026-09-23T22:54:18.620350+00:00）

按用户最新定义，从预置功能抓姿开始，Wuji在现实尺寸参数化刀具上完成滑块伸出/收回；teacher和原本体感觉latent student均已通过冻结后新300初态物理验证。10mm到位换向，两策略各298/300至少完成3轮；student20秒294/300自然存活。外部固定2/5秒指令下，student全部端点10mm末段保持293/297（/300）。60秒快速操作仍会后期掉刀，2mm精度/严格刀身稳定也未解决；桌面取刀、未见物体与真机留后，不重设为本Goal前置条件。

最终报告：`runs/wuji-goal/research/core-teacher-student-final-20260924.md`。原teacher CP25 SHA4d8af063…，原pure latent student最终1000 SHA022ad8c7…；本轮没有新训练或挑峰值，只补齐任务对应的独立验证。刀具为刀身+被动滑块2刚体，147×19×11mm/35g，没有切割接触模型；Wuji控制/物性/奖励与论文有已记录差异，非全参数严格一致。

全部16运行条件已正常退出并重算，四段无字完整20秒视频（两策略×两视角）已检查；失败过程全部保留在证据包。17个资产已上传并验证GitHub SHA256 digest：https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923 。本机包 `runs/wuji-goal/release-core-teacher-student-20260924-v1`；发布清单 `diagnostics/release-core-teacher-student-20260924-verified.json`。主要视频前缀 `wuji-core-teacher-student-20260924`，文件名 `student-arrival-20s-three-grasps.mp4`、`teacher-arrival-20s-three-grasps.mp4`（发布文件含完整前缀）。

数值源pin V2，视频V4/V5源pin，V1–V3失败日志保留；不要修改这些固定目录。完整复现入口/运行命令在Release README。此次Wuji队列已经结束；原本机训练88339保留。四卡Sharpa6250参考训练已完成，八卡原上游参考及现有CP巡检依既定配置继续，不再新增teacher消融来延长本Goal。健康记录最新4h约四卡41.98%、八卡44.12%，完成任务后短窗已低告警，不用无效计算填充。

接续会话先读本段与最终报告，确认用户是否在提出下一项新工作；不要因旧文档中的硬件/宽泛化未完成就误把基本Goal重新判失败。下文为历史过程，涉及仍在训练/等待/工具blocked的表述以此段及goal-state最新工具记录为准。


## 06:45 CST：V4视频完成，补正面视角V5

V4两段无字20s/30fps视频都正常退出且已逐帧抽样检查，三抓姿均实际开合，后段失败保留。原视角主要看到刀身背面/侧面，滑块被遮挡，因此追加V5，仅给同一审计脚本增加相机参数，位置[0,.11,.72]、目标[0,-.11,.55]，不改动作/物理/资产/权重/初态。源pin `core-video-front-20260924-v5` 3686文件验证，八卡GPU1/4队列200297/200298。数值实验仍是V2。两种完整视角一起命名发布，不裁掉失败。

刀具URDF是刀身+被动滑块两刚体参数化模型，没有刀刃/切割接触模型；本任务验证滑块伸缩，与当前“先完成ArtGym式teacher+student、后续取刀”范围一致。模型的现实尺寸不等于物性已实物标定。


## 06:38 CST：全部六种正式数值条件已完成并从物理trace重算

|策略|时长|至少3轮（10mm到位换向）|全程自然存活|平均循环|
|---|---|---|---|---|
|teacher|20s|298/300|191/300|15.37|
|teacher|60s|298/300|143/300|37.20|
|student|20s|298/300|294/300|17.00|
|student|60s|298/300|240/300|42.95|

Student外部固定2秒/5秒指令各300新初态，10mm全部端点末0.3秒保持293/297；原2mm+严格刀身联合126/184；自然存活296/297。符合用户收敛后的基本开合任务，不等于2mm精度或60秒长期可靠。两权重和三个功能抓姿在新300上已验证，未进行新训练、筛行或更换峰值CP。新实验保留Wuji必要差异，不能称完全复现原论文所有参数。

还未完成的本次交付仅为：无字视频生成/检查、打包发布/哈希回读、最终交接和Goal完成标记。V1/V2视频初始化崩溃；V3已修好EGL但顶层assets符号链接导致仿真器相对URDF路径失败。V4把同一源码/资产目录实体化，所有3686hash不变，runner overlay SHA `98f9f5fe050e11742beab29acc9ab02c6a2f4ad71a336dad5a462bf879afa18f`。视频八卡GPU1/4队列197136/197137（新目录V4），前面失败全部保留。

采集：`python -m scripts.collect_wuji_core_evaluation`（数值V2+视频V4）；全14条件队列完成后 `python -m scripts.package_wuji_core_task`，输出 `runs/wuji-goal/release-core-teacher-student-20260924-v1`。检查视频后上传当前Release394720794/Jr-kelly/artgym，验证digest，再标记基本Goal完成。工具当前仍blocked，尚未调用complete。无需额外扩大teacher消融/硬件实验才能完成本次范围。


## 最高优先级：用户澄清 Goal（2026-09-24 06:16 CST）

仿照 ArtGym 的 teacher → student 流程，将 Sharpa 换成 Wuji；从预置功能抓姿开始，在现实尺寸美工刀上学习并闭环完成伸出、收回。完成 teacher 和 student 的仿真验证；桌面取刀、真机标定和广泛未见几何泛化为后续阶段。

详见 `runs/wuji-goal/research/goal-scope-teacher-student-20260924.md`。该范围覆盖下文所有旧“硬件/宽泛化为前提”的表述。已有 teacher 可用，接下来优先原本体感觉 student；保留旧严格指标，补测到位后换向的 10 mm 开合协议。已有 teacher 多 seed 有界收尾，不再扩充消融矩阵。Goal 工具 blocked 与授权实际执行分开记录。


更新时间：2026-09-23T19:45:39.814664+00:00。最新状态以如下03:45段及 research/progress-20260924T0345.md 为准；旧状态存 research/handoff-history-20260924T0345.md。


## 06:28 CST 审计与图形修复（V2）

V1到位换向正式20秒在最后一步断言失败：ArtManip._get_dones把回合超时也放入truncated_envs，原审计只排除了fall/invalid。V2记录timeout并在到位计数中排除，存活指标仍把正常跑满计作存活；没有改仿真、动作、权重或初态。增加真实回合边界语义测试，5测试全部通过。V1预检完成记录有效；正式失败不计成功，失败日志保留。

V1视频在创建图形时-11退出；V2采用已验证RGB运行方式，取消CUDA可见设备重映射、CUDA/Vulkan均指定同一物理GPU、设置NVIDIA ICD。新pin `core-teacher-student-evaluation-20260924-v2`，SHA `bdefce16af75fb0a7d25116b0b2e07f78b543b7bc2239980e0482820d341667c`，3686文件远端验证。队列193656/193657/193658/193659，对应八卡GPU1/3/4/5；无字视频193660/193661按租约等待。原固定时钟四卡任务独立完成，不重复运行。

新的固定2秒300初态结果：旧严格联合126/300；10mm所有五轮末段保持293/300，各组97/100/96；296/300自然存活。当前只引用已完整重算的结果，后续查看 `diagnostics/core-task-collected-20260924-v2/latest.json`。采集命令默认已改为V2；V1记录仍可通过 --version v1读取。

## 当前执行：Wuji teacher + student（2026-09-24 06:23 CST）

先读 `runs/wuji-goal/research/core-teacher-student-evaluation-20260924.md`。冻结原 teacher CP25 和原纯 latent student 最终1000；新300未筛初态已生成，20/60秒到位换向及原固定2/5秒评估已启动。八卡队列191112–191115、四卡327940；无字视频191730/191731按租约等待。Student20秒三个旧预检实际19/16/16循环，不能替代新300。采集命令：`/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.collect_wuji_core_evaluation`，结果 `diagnostics/core-task-collected-20260924-v1/latest.json`。

原 teacher 四新增seed8臂及176项物理/评分已全完成，seed203/204终审同步发布在途；不再扩大teacher消融。新 Goal 以本体感觉student基本开合为优先，旧广泛泛化/硬件门槛不再阻塞。

## 最新接续：2026-09-24 03:45 CST

先读 `research/progress-20260924T0345.md`。严格终止第一seed100和44评估齐：小300/300两时钟、宽279/283，第四0/32，未达广泛泛化。旧终止打包故障已补齐helper，新恢复2876724已在publish；第二reset seed、归一化配对已发布。

四个新增seed201/202/203/204（完整seed20261201–20261204）共8臂100轮配对开始。八卡训练series125766(GPU1,201→203)、125768(GPU3,202→204)；评估series125767(GPU4)、125769(GPU5)；scorers125770–125773。首两臂实际teacher126772/126763，门禁/预检通过。后续seed排队。四本机终审2873738–2873741。source pin `termination-multiseed-20260924-v1`，archive SHA df3d7872d962872a12375e9cc40c5ee90612a5f42fcd3de9bd503198d3b98981。元数据 `diagnostics/termination-multiseed-preparation-20260924-v1.json`，启动 `diagnostics/termination-multiseed-launch-20260924-v1/`。每组所有44旧开发条件，最终须另做新独立验证。

Sharpa四个CP3000/4000×100随机评估齐，共114800试验，矩阵重算通过。原/修复执行SR：53.22/55.88%，52.09/54.44%；GC未持续改善，不是严格公式复现。长训练约5950/6250(corrected)、4750/6250(upstream)。03:35滚动4h四卡45.46%、八卡33.59%，八卡短窗低告警；新任务03:44瞬时65.75%，不能当长期均值。原4090 PID88339保留且实查。

## 历史核验：2026-09-23 23:08 CST

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


终止配对发布修复完成 2026-09-23T20:05:22.109484+00:00：runs/wuji-goal/diagnostics/release-termination-pair-complete-20260924-v2-verified.json，全部附件digest通过，0新增物理。


## 自动更新：终止阈值seed20261202完整审计 2026-09-23T21:24:03.411190+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261202-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261202-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：终止阈值seed20261201完整审计 2026-09-23T21:29:03.789159+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261201-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261201-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 当前工作与目标核对：2026-09-24 06:08 CST

本轮远端实查：新增四seed共8臂100epoch全部正常完成；seed201/202各44评估和评分完成；seed203完成41/44物理、38评分，seed204完成42/44物理、39评分，两评估和评分进程仍活跃。之前03:45“首两臂训练中”已过时。

最终用户目标仍为现实尺寸刀具上的Wuji学习策略完整开合，经过可追溯论文参考/迁移实验、独立评估、可部署student与实际标定后真机执行。当前多seed只检验严格终止的收益是否稳定，不解决未见抓姿和未标定物性。该轮收齐后优先分析抓姿/接触及滑块阻力鲁棒性与物理参数假设，再冻结候选开展新独立验收；避免继续用重复seed替代真实迁移缺口。Sharpa是方法/实现参考线，GPU利用率是运行约束，均不替代Wuji实际任务成功。


## 自动更新：终止阈值seed20261204完整审计 2026-09-23T22:41:19.008128+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261204-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261204-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：终止阈值seed20261203完整审计 2026-09-23T22:47:04.333058+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261203-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261203-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。
