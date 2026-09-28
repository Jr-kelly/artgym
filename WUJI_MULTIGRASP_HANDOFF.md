# 最新续接：多抓姿核心对照完成，专家诊断运行（2026-09-28T20:26:23.276846+00:00）

Goal仍active，禁止子代理。工作区`/data/research/artgym-experiments-20260921/multigrasp-20260928`，分支`feat/wuji-multigrasp-2x2-20260928`。总截止2026-09-29 02:53:52UTC，01:53:52留最终交付。

四臂1000轮全部完成，16CP本地备份/CPU哈希核验；同预算final1000-v1的16项800初态物理评估完成，独立复算passed。fixed2严格A9/B0/C19/D0/reference94，fixed5 A/B/C/D0/reference93。每组800，严格全部集中原训练。详`research/multigrasp-20260928/README.md`和`final1000-analysis/`。所有新训练/历史/新测试严格均0，旧teacher未被替代。

四开发冻结A750/B1000/C750/D1000。`selected-v1`当前GPU0实际继续（队列95255，需实查），同800初态/同GPU；最终状态`runs/multigrasp-20260928/selected-v1/results.json`远端，尚未结束。新测试原门禁两批均0；第二批53候选中的1/16/29除了触觉代理均有效，明确物理门禁修订后在策略评估前全部冻结补充集，不冒充原预注册盲测。最终800静态687alive/656stable；新96中42alive/30stable(2bases)，全部策略严格0。

唯一后续主要诊断已20:11UTC启动：单抓姿专家源3/5/11，GPU1/2/3，trainPID104797/104799/104800，名字expert_row3_seed2810等；各1000轮、5120env、span.04、seed2026092810，同初始化tensorSHA0ad7813cc00ba3d935547e9f42bf0ca467f6683e47306317f3f400779716e94b。4h wrapper有界，预计23:30前后完成，要按真实吞吐核查。独立32源扰动final1000评估等待PID106197/106198/106199；脚本evaluate_wuji_multigrasp_expert.py，00:30截止等待，4个协议每项600s。无其它诊断分支。

Release草稿`wuji-multigrasp-20260928-v1` id398592814已创建；四权重包16CP服务端SHA成功。五份final1000原始trace包正在上传，工具session76209，可poll，不要重复覆盖资产。大trace>100MB未入git，小JSON/CSV已入。恢复入口restore_wuji_multigrasp_weights.py已对全部16验证，通过；reference.pth另在delivery/wuji-historical-reference.pth待上传。draft GET by tag404，gh api releases列表按id操作。最终发布后URL中untagged需重新从API获取正式地址。

本轮A1000视频已完成`videos/A1000-three-grasps.mp4`，实际0/3strict/2alive(原主表成功行重仿真最后端点失败)，差异明确；旧reference成功视频保留。frames0/150/300/450/599实检。可加专家成功/失败视频，但不得把现视频标严格成功。

最新已commit0651f91，push工具session58779待poll确认；此前2825f0f已push。原四训练均结束；本地无训练，上传/原monitor仍运行，备份16/16完成。必须重新实查所有PID和资源，不依据此文重启。当前下一步：完成selected表并独立复算、检查专家吞吐和结果，补专家权重/视频与报告，Release全部资产SHA/恢复测试，最终push核验。研究任务尚未全部交付，不能标Goalcomplete。

---

# 多抓姿Goal最新接续 2026-09-28T15:31:43.019779+00:00

本轮有进展：代表旧teacher视频和开发初态实际检查已push7537334（四组训练仍未完成），报告research/multigrasp-20260928/README.md，视频videos/reference-three-grasps-policy.mp4。本机物理已结束。四H100训练持续，最新实查A141/B108/C128/D71；D之后已观察epoch76，勿据历史PID重启。D最新wrapper9453接管原4716训练，6h看护至21:10UTC（原4h预计不足），原训练PID/startticks/租约/1000轮预算不变；开发D等待器v2见development-D-waiter-v2.json。其它A/B/C wrapper原样。总截止09-29 02:53:52UTC不变。

128开发扰动静态alive128，strict body127，不据此筛去失败。新seed2803物理联合门禁0合格；追加seed2805最多3000仍afterA，之后A开发评估；新抓姿门禁脚本freeze_wuji_multigrasp_test.py可直接收第二批，但先跑实际静态/几何筛选。最终prepare_wuji_multigrasp_frozen_cohort.py要求四个development-X/frozen.json存在后生成同批最终扰动，evaluate_wuji_multigrasp_frozen.py统一GPU顺序跑static+四组及旧reference各2s/5s/arrival；这些最终入口尚未运行，不能当结果。

下一项：检查真实训练进程/吞吐与超时余量，等待同预算四组完成；按预注册开发选CP和物理有效新测试完成冻结比较，再据实选唯一诊断、代表新策略视频并GitHub交付。不得停留在此中间交付、不标Goal完成。详细历史如下。

# 多抓姿2×2 Goal 实际续接（2026-09-28T15:19:00.569063+00:00）

本轮原生Goal active，禁止创建子代理。主根 `/data/research/artgym-experiments-20260921/multigrasp-20260928`，独立分支 `feat/wuji-multigrasp-2x2-20260928`，已push7759dd3，后续增量待提交。绝对截止2026-09-29 02:53:52 UTC，01:53:52 UTC至少留评估交付；不要重启已运行实验。

四H100主机 `.93:30296`，ssh key `/home/agiuser/.ssh/id_ed25519_h200`，远端根 `/home/wangjiarui/artgym-multigrasp-20260928`，python `/home/wangjiarui/artgym-runtime/bin/python`。A GPU0/C GPU1/B GPU3/D GPU2，各seed2026092801，1000epoch×5120×32，全部真正训练中；首次同随机初始化tensor SHA bdf13bb79563529617cba46355011a9d857f1fdefe13f2a8279de8a0458f66b4。初始实测每epoch10–15秒；监控器14400秒上限要持续核查more组吞吐，不能超时当方法失败。任务实际进程/命令在 `research/multigrasp-20260928/receipts/monitor-latest.json`，必须重查。

原3记录/更多16记录含原3，按既有5mm/.05rad/5°关节RMS实际2/15构型簇。数据manifest/preregistration已冻结。全部方法配置审计passed，除名称只差池和span .04/.20；实际训练reset/动作门禁20800交互通过。资产固定旧刀SHA5229c66b...，参考旧teacher4d8af063...；新模型从随机开始，未用旧teacher微调。源码训练相关不得在途修改。

新测试seed2803生成1000，24通过初始物理，21/24静态20s存活，但固定姿态+拇指完整行程0合格。所有失败保留，不报告不存在的盲测成功。追加seed2805最多3000已排队after A，GPU0先生成再A开发评估，生成代码已同步，输出fresh-generation-3000。该补充不是新主要诊断，不按策略成绩筛选。第二批完成后需同步缓存、复用独立静态/几何筛选，再冻结新测试；不能只依赖原0/32历史抓姿。

各臂后续开发队列已真实启动等待：`development-queues.json`，A after fresh-generation-v2，B/C/D after各自训练；CP250/500/750/1000 ×2/5秒，共每臂8条件，16个联合训练记录×8扰动=128，严格指标等权最高、平局latest。每臂输出development-X/frozen.json；新测试不参与选择。尚未设置最终冻结测试队列，需结合第二批物理数据执行；最终需要同GPU协议四组+旧参考、分基础抓姿统计、必要关键seed/单抓姿专家最多一主要分支、代表性视频、打包GitHub交付。

本机4090仅ToDesk等桌面进程保留，无旧训练进程。已跑实际补充：static-candidates-local-v1 24/24存活；reference-candidates-t2-v1旧teacher18/24存活、9/24第一完整开合、5/24严格（原3+2重复，去重复3/22），额外4开合但刀身不稳，不能提前判根因。reference-candidates-t5-v1现在运行，重新查PID。接触通道顺序thumb/index/middle/ring/pinky；关节顺序index/middle/ring/pinky/thumb。初版离线接触标签错位已保留*.invalid-contact-order.json，正确*-contact-order-v2.json；物理/成功指标不变。

本地镜像monitor PID3671366，有界42000s，只读同步每30秒；旧监控/其它任务不动。远端所有子job通过租约/超时运行。最新报告 `research/multigrasp-20260928/README.md`。Git直接push在外部worktree的辅助进程读config出现EPERM，安全路径：rsync common.git到 `/tmp/wuji-multigrasp-publish.git`（排除worktrees/index/logs），从/tmp使用`git --git-dir=... -c core.bare=true push https://github.com/Jr-kelly/artgym.git refs/heads/feat/wuji-multigrasp-2x2-20260928:refs/heads/feat/wuji-multigrasp-2x2-20260928`。提交用`git -c user.name=wangjiarui -c user.email=Jr-kelly@users.noreply.github.com commit`，不改共享全局配置。无token输出。已有push ls-remote核验。

下一项唯一执行重点：让四臂同预算训练与开发评估正常完成，同时补足物理有效的新测试抓姿并冻结；不能把训练启动或静态通过称完成。全部已有v2/旧成功链路保留，本轮无真机动作。


多抓姿 2026-09-28T14:59:41.711893+00:00 启动请求 static-candidates-v1 GPU0 .93:30296；证据 runs/multigrasp-20260928/static-candidates-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:00:33.221687+00:00 启动请求 scratch-small-preflight-v1 GPU1 .93:30296；证据 runs/multigrasp-20260928/scratch-small-preflight-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:02:58.158814+00:00 启动请求 fresh-generation-v1 GPU2 .93:30296；证据 runs/multigrasp-20260928/fresh-generation-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:03:03.023195+00:00 启动请求 mg_D_preflight_v1 GPU3 .93:30296；证据 runs/multigrasp-20260928/mg_D_preflight_v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:04:06.476219+00:00 启动请求 mg_B_seed2801 GPU3 .93:30296；证据 runs/multigrasp-20260928/mg_B_seed2801，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

## 多抓姿2×2实查 2026-09-28T15:05:29.079713+00:00

A/C/B actual running, D preflight passed then queued after new test generation; 1000epochs x5120x32 each, same initial model bdf13bb...。24/24 alive20s; duplicate2 records; max drift2.36mm, max rotation.155rad; not operation success。新测试seed2026092803仅物理筛选，GPU2生成后D接续。实查任务/PID/初始模型哈希：`/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/latest-jobs.json`。总截止02:53:52 UTC，01:53:52 UTC留评估交付；不影响v2任务。下一项：verify D start and fresh candidates; finish fixed 1000epochs per arm; dev selects CP250/500/750/1000; new test remains unused。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_A_seed2801 running；远端PID 2449；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_C_seed2801 running；远端PID 2499；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 fresh-generation-v1 running；远端PID 2870；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 static-candidates-v1 completed；远端PID 1098；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 scratch-small-preflight-v1 completed；远端PID 1343；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_D_preflight_v1 completed；远端PID 2551；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_B_seed2801 running；远端PID 3149；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿 2026-09-28T15:10:27.402115+00:00 本机4090实查无计算进程，启动 runtime-more-span20-v1 PID3691986；命令与权重/配置见 runs/multigrasp-20260928/runtime-more-span20-v1；待终结核验。

多抓姿实查 2026-09-28T15:10:29.549370+00:00 fresh-generation-v1 completed；远端PID 2870；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:10:29.549370+00:00 mg_D_seed2801 running；远端PID 4716；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿 2026-09-28T15:11:23.099250+00:00 本机4090实查无计算进程，启动 fresh-static-v1 PID3697881；命令与权重/配置见 runs/multigrasp-20260928/fresh-static-v1；待终结核验。

## 多抓姿2×2实查 2026-09-28T15:13:16.823470+00:00

A/C/B actual running, D preflight passed then queued after new test generation; 1000epochs x5120x32 each, same initial model bdf13bb...。24/24 alive20s; duplicate2 records; max drift2.36mm, max rotation.155rad; not operation success。新测试seed2026092803仅物理筛选，GPU2生成后D接续。实查任务/PID/初始模型哈希：`/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/latest-jobs.json`。总截止02:53:52 UTC，01:53:52 UTC留评估交付；不影响v2任务。下一项：verify D start and fresh candidates; finish fixed 1000epochs per arm; dev selects CP250/500/750/1000; new test remains unused。

多抓姿 2026-09-28T15:14:33.857577+00:00 本机4090实查无计算进程，启动 reference-candidates-t2-v1 PID3717322；命令与权重/配置见 runs/multigrasp-20260928/reference-candidates-t2-v1；待终结核验。

## 多抓姿实际进展 2026-09-28T15:14:33.876750+00:00

四组A/B/C/D均正式运行（D 15:10:29UTC PID4716）；1000epochs预算不变。新seed2803生成1000/物理初筛24通过，实际20s静态21/24存活，固定姿态+拇指全行程0合格，无新盲测可用；保留完整失败，未用策略筛选。已排队seed2805最多3000补充生成，在A训练结束后同GPU0串行，之后A开发评估；B/C/D各自结束后8项CP×2/5s开发评估。队列脚本与命令在research/multigrasp-20260928/*queues.json及fresh2-queue.json。严格选CP只读开发集。运行时more/.20已实际20800交互通过，130次动作映射一致，所有16基础记录均采样。
本机补充实际冻结参考评估；先前“无计算进程”应精确为无训练/仿真进程：ToDesk_Session PID266663占651MiB保留。旧监控/桌面未干扰。Git直接push因git辅助进程读取外部worktree配置EPERM失败；已通过/tmp/wuji-multigrasp-publish.git独立镜像成功push7759dd3并ls-remote核验。非训练失败。下一项：收集参考分抓姿结果，冻结第二批物理筛选，等待四组同预算完成。

多抓姿 2026-09-28T15:16:28.653902+00:00 本机4090实查无计算进程，启动 static-candidates-local-v1 PID3728900；命令与权重/配置见 runs/multigrasp-20260928/static-candidates-local-v1；待终结核验。

多抓姿 2026-09-28T15:19:00.554304+00:00 本机4090实查无计算进程，启动 reference-candidates-t5-v1 PID3744256；命令与权重/配置见 runs/multigrasp-20260928/reference-candidates-t5-v1；待终结核验。

2026-09-28T15:20:58.009740+00:00 实查四臂epochs A94/B69/C85/D37，继续。最新push8bec6f4；5minGPU86.375%，重启以来1688.5s均值53.7098%，不是完整4h。下一项同预算训练/自动开发评估、新生成测试物理门禁。

多抓姿 2026-09-28T15:22:29.235418+00:00 本机4090实查无计算进程，启动 reference-video-success-failure-v1 PID3765605；命令与权重/配置见 runs/multigrasp-20260928/reference-video-success-failure-v1；待终结核验。

## 多抓姿 2026-09-28T15:25:30.366571+00:00 reference_video_and_fresh_screen_terminal

上一goal轮为progress；本轮再次实查四训练PID2449/2499/3149/4716均存活。旧teacher5秒严格5/24（原3及2重复），19/24存活。新seed2803最终物理门禁0合格。三抓姿20秒视频完成并检查600帧；1/3严格、3/3存活，行5小batch未复现24-env掉落，已明确标注。 证据：research/multigrasp-20260928/videos/manifest.json, research/multigrasp-20260928/data/fresh2803-frozen/manifest.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1524.json。下一步：保留四组1000epoch训练，监测D四小时job上限余量；等新3000生成后物理筛选并执行冻结最终评估。

多抓姿 2026-09-28T15:26:02.034277+00:00 本机4090实查无计算进程，启动 dev-static-precheck-v1 PID3788253；命令与权重/配置见 runs/multigrasp-20260928/dev-static-precheck-v1；待终结核验。

## 多抓姿 2026-09-28T15:28:23.771227+00:00 development_static_completed

128开发扰动全部静态存活，127/128全程刀身稳定；base7一扰动未过严格稳定，保留全部行并单列，不调阈值。代表视频已push001b043并HTTP200/远端commit核验。当前本机仿真全部结束，四H100训练仍在运行，未新增主要诊断。 证据：research/multigrasp-20260928/development-static-validity.json, research/multigrasp-20260928/videos/manifest.json。下一步：四组1000epoch与已排队开发评估，补充新测试抓姿；留出冻结评估和最终提交时间。

## 多抓姿 2026-09-28T15:31:03.581214+00:00 D_supervisor_extended_preserving_training

D预测总时长超过原4h看护上限；验证子进程保留GPU租约后只替换旧wrapper4715为9453，实际训练PID4716/start ticks保持，已继续到epoch76。总看护上限6h（至21:10UTC），仍早于全轮截止；交互预算1000轮不变，未重启训练。相应等待开发评估的5985仅等待进程替换为v2，防止等待时限早于训练。一次收据复制命令地址拼写错误后已用正确入口完成，无训练失败。 证据：research/multigrasp-20260928/receipts/D-supervisor-adoption.json, research/multigrasp-20260928/development-D-waiter-v2.json。下一步：继续四臂训练，检查真实PID/最后20轮吞吐；训练完毕由既定开发队列冻结checkpoint。

## 多抓姿 2026-09-28T15:32:19.951944+00:00 progress_increment_verified

本轮进展已push并ls-remote核验6e674fa2484b5ddb0c7f32110e2f015b48cad2a4。四训练实际PID2449/2499/3149/4716再查存活，D接管后继续epoch82；9453看护和9766等待开发均存活。Goal未完成，继续同预算训练。 证据：research/multigrasp-20260928/receipts/D-supervisor-adoption.json, research/multigrasp-20260928/videos/manifest.json, research/multigrasp-20260928/development-static-validity.json。下一步：训练完成与已排队开发评估；新测试物理筛选后统一冻结评估。

多抓姿 2026-09-28T15:33:24.636011+00:00 本机4090实查无计算进程，启动 reference-candidates-arrival-v1 PID3835302；命令与权重/配置见 runs/multigrasp-20260928/reference-candidates-arrival-v1；待终结核验。

## 多抓姿 2026-09-28T15:34:22.722643+00:00 fresh2_physical_followup_queued

前轮为progress。重新实查A162/B126/C147/D86均真实运行，未重启。新增本机有界等待PID3838398，第二批3000生成完成后自动同步全候选，执行预先固定几何/20s静态门禁并冻结全部合格新抓姿；不加载操作策略成绩筛选，无新增训练。原0合格批次保留。 证据：research/multigrasp-20260928/fresh2-local-continuation-launch.json, runs/multigrasp-20260928/fresh2-local-continuation/status.json。下一步：继续四训练及第二批物理筛选；开发集冻结权重后完成同初态最终对照。

## 多抓姿 2026-09-28T15:36:49.830864+00:00 reference_both_protocols_completed

旧冻结teacher实际到位换向20s评估完成；去逐位重复22抓姿：static22/22存活，固定2/5s第一轮均7/22、全部严格均3/22；arrival至少3轮7/22，16/22alive。13新增训练来源中4能开合但0严格；6历史诊断固定开合0。每基姿1回合，仅开发诊断，不代替新测试或四臂结论。 证据：research/multigrasp-20260928/reference-by-grasp.csv, research/multigrasp-20260928/reference-summary.json, research/multigrasp-20260928/evidence/reference-candidates-arrival-v1/evidence/report.json。下一步：四正式训练继续，等待各1000epoch和开发冻结，第二批新测试物理筛选已排队。

## 多抓姿 2026-09-28T15:37:32.850214+00:00 reference_protocol_increment_pushed

已push并远端核验aaf65578484d82d8c6eae37b7140aa215827bab3。四训练原PID2449/2499/3149/4716实查均live；GPU即时94/89/80/91%。上一轮与本轮均有实际证据进展，当前下一关键结果需等待训练。新测试后续实际等待PID3838398，不重启既有任务。 证据：research/multigrasp-20260928/reference-summary.json, research/multigrasp-20260928/fresh2-local-continuation-launch.json。下一步：继续已验证存活的四训练到1000；开发评估后冻结权重；追加新抓姿物理门禁和最终统一测试。

## 多抓姿 2026-09-28T15:40:20.533260+00:00 four_checkpoint_integrity_passed

四组已保存CP10均CPU加载成功、48模型张量有限、epoch10与1638400交互一致、含优化器与RNN状态。仅完整性检查，不运行CP10策略或选择权重。最新实查A190/B149/C173/D106均live，D看护余量105min；B预测看护余量22min，需要继续监测。 证据：research/multigrainvalid.json, research/multigrasp-20260928/receipts/checkpoints-cp10-cpu-audit.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1538.json。下一步：保留训练运行至1000轮；检查保存的CP250/500/750/1000和队列衔接。

## 多抓姿 2026-09-28T15:40:43.990534+00:00 evidence_path_correction

上一条four_checkpoint_integrity_passed误附了一个不存在的research/multigrainvalid.json路径；该路径无证据效力。两份真实checkpoint/进程收据均存在，结论不变。事件记录入口现要求全部证据路径存在后才追加，原失败记录保留。 证据：research/multigrasp-20260928/receipts/checkpoints-cp10-cpu-audit.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1538.json。下一步：继续既有训练及有界等待，不重启或扩大实验。

## 多抓姿 2026-09-28T15:42:54.295444+00:00 training_source_unchanged_verified

四臂继续运行至A212/B167/C193/D122，八个核心训练、控制、观测、PPO源码远端/本地/初始manifest哈希全部一致；后续评估与看护变更没有修改在途训练逻辑。 证据：research/multigrasp-20260928/receipts/training-source-unchanged-1543.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1542.json。下一步：等待训练产生预注册checkpoint并继续至1000轮。

## 多抓姿 2026-09-28T15:52:36.900583+00:00 A_checkpoint250_verified_and_backed_up

A首个预注册CP250实际保存，CPU核验250轮/40960000交互、48模型张量有限、optimizer/RNN完整；远端与本地备份SHA256一致：7bb42b50049dd72c718e2b8f4dacf15c02f5f1061bae049d58981e68fdc29ecf。此CP未评估/未选择，四训练原进程继续。 证据：research/multigrasp-20260928/receipts/checkpoints-cp250-first-20260928.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1550.json, runs/mg_A_seed2801/checkpoints/epoch_000250.pth。下一步：继续1000轮训练，保留统一开发选CP和冻结测试；新测试补充生成/物理筛选仍有界排队。

## 多抓姿 2026-09-28T15:53:31.777267+00:00 checkpoint_increment_push_verified

增量4f5b567725f2f643983d46680fed70aa23b00531已push/ls-remote核验。最后实查训练A260/B207/C236/D156，A250权重本地备份完整；本地监控3671366/新测试后续3838398仍存活。当前属于有实际checkpoint证据的progress，Goal未完成。 证据：research/multigrasp-20260928/receipts/checkpoints-cp250-first-20260928.json, research/multigrasp-20260928/receipts/process-throughput-20260928T1550.json。下一步：既有四臂训练继续1000轮及排队开发评估，之后冻结最终比较。

## 多抓姿 2026-09-28T15:56:04.381956+00:00 milestone_backup_verified

Backed up immutable A-250 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/A-250.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T15:56:05.429698+00:00 milestone_backup_verified

Backed up immutable C-250 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/C-250.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T15:56:30.043205+00:00 checkpoint_backups_armed

C250已CPU核验通过并回传备份；A/C250均为40960000交互，未评估或选择。启动有界16候选权重备份PID3979625：只在原子metadata发布后复制CP250/500/750/1000并核对远端本地SHA；保留训练原进程，7.5h上限早于本轮截止。 证据：research/multigrasp-20260928/receipts/cp250-AC-1555.json, research/multigrasp-20260928/checkpoint-backup-launch.json。下一步：继续四臂训练至1000；同步新抓姿物理筛选与预注册开发选择。

## 多抓姿 2026-09-28T16:02:04.907190+00:00 ABC250_checkpoints_integrity_pass

A/B/C三臂已到CP250，三个候选CPU核验250轮/40960000交互及模型有限性通过；D仍在训练尚未到250。各臂训练继续1000轮，未运行候选策略或选CP。自动备份逐份核验，实际看护/物理筛选等待仍live。 证据：research/multigrasp-20260928/receipts/cp250-ABC-1601.json, research/multigrasp-20260928/receipts/checkpoint-backups/status.json。下一步：继续四臂1000轮及开发评估，物理有效新测试筛选等待原排队生成。

## 多抓姿 2026-09-28T16:02:17.679014+00:00 milestone_backup_verified

Backed up immutable B-250 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/B-250.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T16:02:36.947040+00:00 matched_final_checkpoint_protocol_added

在最终测试尚未运行前明确两张表：四臂CP1000均163840000交互的同预算主对照，以及原定开发集择优CP的部署候选表。新增final1000入口校验epoch/frame，不修改训练、开发规则、数据或阈值。两个选择均必须先冻结开发决策再看最终数据。 证据：scripts/evaluate_wuji_multigrasp_frozen.py, research/multigrasp-20260928/README.md。下一步：训练完成后对相同有效初态运行final1000与开发择优冻结评估，分开报告。

## 多抓姿 2026-09-28T16:06:53.016840+00:00 final_analysis_realtrace_validated

最终分析补充逐回合时序诊断，已在旧参考2s/5s/arrival三套真实轨迹共72回合复算，与原报告完全一致；固定严格端点由独立代码交叉核验。首次路径少一层evidence读取失败，修正后通过，无新物理或权重选择。增量a3db8f2远端核验通过。 证据：research/multigrasp-20260928/receipts/final-analysis-realtrace-validation.json, scripts/analyze_wuji_multigrasp_frozen.py。下一步：四训练继续1000轮，开发冻结后运行同预算及开发择优两套正式测试。

## 多抓姿 2026-09-28T16:16:34.523291+00:00 milestone_backup_verified

Backed up immutable D-250 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/D-250.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T16:17:35.381774+00:00 all_four_cp250_integrity_pass

D250已备份；四臂CP250全部CPU加载检查通过，epoch250/frame40960000，模型张量有限且含优化器。D权重SHA40ad0ffd114a58fbee04043975bd974917a414509f2ad1a76af52b755f1c10ef；四正式训练继续，无提前策略测试或选择。 证据：research/multigrasp-20260928/receipts/cp250-ABCD-1617.json, research/multigrasp-20260928/receipts/checkpoint-backups/D-250.json。下一步：继续1000epoch及预注册开发评估，待新测试物理门禁后冻结正式比较。

## 多抓姿 2026-09-28T16:36:58.949887+00:00 milestone_backup_verified

Backed up immutable A-500 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/A-500.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T16:37:35.959615+00:00 A_cp500_and_full_analyzer_validation

A500已真实保存及CPU完整性核验（81920000交互），所有四臂250已备份。正式分析入口用旧参考重用构造的验证夹具完整执行，通过360行CSV/JSON、相同输入零因素差、时序及独立评分检查；夹具不是四臂结果且临时输出已删除。训练A501/B405/C457/D331在16:36UTC实查存活，B看护余量17.8min。 证据：research/multigrasp-20260928/receipts/cp500-first-1638.json, research/multigrasp-20260928/receipts/final-analysis-export-validation.json。下一步：继续同预算训练及后续开发评估；优先检查实际进程和B超时余量。

## 多抓姿 2026-09-28T16:39:00.371421+00:00 contact_gate_limitation_audited

离线核查发现原参考成功抓姿0和2也不满足新测试>=3非拇指二值触觉95%门禁；触觉净力阈值不是逐物体接触身份，故门禁保守且非可操作性的必要条件。保留本轮预注册筛选不放宽。首批仍独立因姿态+拇指路径0合格；零合格不能推断无可操作新姿态。 证据：research/multigrasp-20260928/receipts/contact-gate-sensitivity.json。下一步：继续四臂训练；第二批按原物理门禁完成，同时明确筛选适用范围。

## 多抓姿 2026-09-28T16:46:09.371737+00:00 milestone_backup_verified

Backed up immutable C-500 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/C-500.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T16:59:23.179913+00:00 milestone_backup_verified

Backed up immutable B-500 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/B-500.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T16:59:29.445883+00:00 ABC_cp500_utilization_verified

A/B/C500权重已CPU核验epoch500/frame81920000且模型有限，D仍继续。实测15:07至16:59UTC整机采样时加权利用率86.28%，覆盖1.86h，尚非平台4h口径；未运行填充计算。四臂16:59UTC A618/B502/C566/D419，B看护余量约16.9min，维持现有看护。 证据：research/multigrasp-20260928/receipts/cp500-ABC-1700.json, research/multigrasp-20260928/receipts/utilization-audit-1700.json。下一步：继续至统一1000轮；收集第二批新测试与开发冻结，之后完整比较。

## 多抓姿 2026-09-28T17:19:44.071752+00:00 milestone_backup_verified

Backed up immutable D-500 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/D-500.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T17:19:58.354401+00:00 all_four_cp500_integrity_pass

四组原进程实查A728/B592/C667/D502，已全部达到CP500并CPU核验81920000交互和张量完整性；同预算1000训练未完成。B看护预计余量15.9min，D约119min训练剩余，继续原训练。最终分析全流程验证通过，正式策略评估仍等待开发冻结。 证据：research/multigrasp-20260928/receipts/cp500-ABCD-1720.json。下一步：完成四臂1000及队列开发评估，第二批新测试物理门禁后统一冻结比较。

## 多抓姿 2026-09-28T17:23:50.339037+00:00 milestone_backup_verified

Backed up immutable A-750 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/A-750.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T17:37:08.781591+00:00 milestone_backup_verified

Backed up immutable C-750 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/C-750.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T17:37:39.955001+00:00 AC_cp750_integrity_pass

A/C达到750并CPU核验122880000交互、有限模型及优化器状态；A822/B668/C752/D572在17:37UTC均原训练进程存活。整机即时97/97/95/98%，B看护余量约14.5min，尚未需接管；A预计约32min训练剩余。 证据：research/multigrasp-20260928/receipts/cp750-AC-1738.json。下一步：A终结后核查新测试生成衔接，C终结后开发评估；四组保持1000同预算。

## 多抓姿 2026-09-28T17:56:24.449847+00:00 ABC_cp750_integrity_pass

A/B/C750均CPU核验122880000交互及模型完整性；四训练17:56UTC A922/B750/C842/D647，原PID不变。预计A14min/C32min/B55min/D84min剩余，B看护余量13.5min；后续生成与开发等待器已实际核查存活。 证据：research/multigrasp-20260928/receipts/cp750-ABC-1757.json。下一步：首先核验A1000终结与第二批新抓姿生成实际启动；不抢占其它卡。

## 多抓姿 2026-09-28T17:56:27.705772+00:00 milestone_backup_verified

Backed up immutable B-750 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/B-750.json。下一步：Continue fixed1000epoch training and preregistered development selection。

多抓姿 2026-09-28T18:10:45.935558+00:00 启动请求 mg_A_seed2801 GPU0 .93:30296；证据 runs/multigrasp-20260928/mg_A_seed2801，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿实查 2026-09-28T18:11:04.457470+00:00 mg_A_seed2801 completed；远端PID 2449；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:11:04.457470+00:00 fresh-generation-v2 running；远端PID 67680；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:11:43.122935+00:00 milestone_backup_verified

Backed up immutable A-1000 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/A-1000.json。下一步：Continue fixed1000epoch training and preregistered development selection。

## 多抓姿 2026-09-28T18:11:56.238241+00:00 A_full_budget_complete_fresh2_started

A正式训练于18:10:45UTC正常exit0终结，11325.45s墙钟，CP1000 CPU核验163840000交互并已本地哈希备份。第二批seed2805/3000候选生成18:10:48自动接续，wrapper67679/child67680实际运行GPU0。B816/C914/D708仍原PID训练；未选任何模型。 证据：research/multigrasp-20260928/receipts/cp1000-A-1812.json, runs/multigrasp-20260928/mg_A_seed2801/status.json, research/multigrasp-20260928/receipts/monitor-latest.json。下一步：接续新测试物理筛选与四组开发冻结，之后同初态final1000和择优两张表。

## 多抓姿 2026-09-28T18:12:19.249579+00:00 final_analysis_tools_synced

最终两种选择入口和已验证分析脚本同步远端，仅评估/离线工具；未修改在途训练源码。后续同GPU冻结比较使用final1000和development两张表。 证据：scripts/evaluate_wuji_multigrasp_frozen.py, scripts/analyze_wuji_multigrasp_frozen.py。下一步：继续既有训练/生成队列，先收齐开发frozen.json并冻结最终初态。

## 多抓姿 2026-09-28T18:21:54.869419+00:00 milestone_backup_verified

Backed up immutable D-750 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/D-750.json。下一步：Continue fixed1000epoch training and preregistered development selection。

多抓姿 2026-09-28T18:29:17.584487+00:00 启动请求 mg_C_seed2801 GPU1 .93:30296；证据 runs/multigrasp-20260928/mg_C_seed2801，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿实查 2026-09-28T18:29:39.125739+00:00 mg_C_seed2801 completed；远端PID 2499；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:29:39.125739+00:00 dev-C-cp250-t2 running；远端PID 74944；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:30:06.455499+00:00 milestone_backup_verified

Backed up immutable C-1000 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/C-1000.json。下一步：Continue fixed1000epoch training and preregistered development selection。

多抓姿实查 2026-09-28T18:30:11.178515+00:00 fresh-generation-v2 completed；远端PID 67680；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:30:11.178515+00:00 dev-A-cp250-t2 running；远端PID 75200；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:30:38.452392+00:00 C_full_budget_complete_development_started

C正式训练18:29:17UTC正常exit0完成1000轮，12435.88s墙钟；A/C最终CP1000均CPU核验163840000交互，四组750也完整。C开发首项实际PID74944在GPU1运行，128新扰动。第二批3000生成完毕并进入第一阶段物理筛选，尚未冻结新测试。 证据：research/multigrasp-20260928/receipts/cp1000-AC-1830.json, research/multigrasp-20260928/receipts/cp750-ABCD-1830.json, runs/multigrasp-20260928/mg_C_seed2801/status.json。下一步：收集C八项开发/第二批物理门禁，B/D继续1000后开发；四权重全冻结后最终测试。

多抓姿实查 2026-09-28T18:31:14.083400+00:00 dev-C-cp250-t2 completed；远端PID 74944；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:31:14.083400+00:00 dev-C-cp250-t5 running；远端PID 75828；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:32:18.135342+00:00 fresh2_sync_failure_fixed

第二批生成1147.97s正常完成；本地接续3838398因rsync父目录缺失退出，未进入几何或物理筛选。失败日志/status保留；脚本补mkdir并以独立v2目录重启只读同步+既定物理筛选，不重跑生成。新PID见收据，仍截止23:53UTC。 证据：runs/multigrasp-20260928/fresh2-local-continuation-launcher.log, research/multigrasp-20260928/receipts/fresh2-continuation-v2.json, scripts/collect_wuji_multigrasp_fresh2.py。下一步：检查v2几何/静态筛选完成，再冻结全部合格新测试；各臂开发继续。

多抓姿实查 2026-09-28T18:32:17.492373+00:00 dev-A-cp250-t2 completed；远端PID 75200；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:32:17.492373+00:00 dev-A-cp250-t5 running；远端PID 76092；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:33:22.463479+00:00 dev-C-cp250-t5 completed；远端PID 75828；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:33:22.463479+00:00 dev-C-cp500-t2 running；远端PID 76630；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:33:49.036429+00:00 fresh2805_physical_screen_complete

Second3000generated candidates physically screened without learned-policy selection; qualified base count 0 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/data/fresh2805-frozen/manifest.json。下一步：Freeze four models using development then run final identical-cohort comparison。

多抓姿实查 2026-09-28T18:33:54.852459+00:00 dev-A-cp250-t5 completed；远端PID 76092；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:33:54.852459+00:00 dev-A-cp500-t2 running；远端PID 76883；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:34:58.645372+00:00 dev-C-cp500-t5 running；远端PID 77245；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:34:58.645372+00:00 dev-C-cp500-t2 completed；远端PID 76630；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:35:45.273708+00:00 supplemental_unseen_pool_frozen_before_policy

第二批53候选49静态存活，原门禁0合格；其中1/16/29全通过姿态/拇指路径/非旧family/20s存活/刀身稳定，仅触觉代理失败。在新抓姿策略结果未运行前，三者全部冻结为new_unseen_amended_physical补充集，明确事后物理门禁修订，不冒充原预注册盲测。旧0合格manifest原样保留，无按策略筛选、无新增生成。 证据：research/multigrasp-20260928/data/fresh2805-frozen/manifest.json, research/multigrasp-20260928/data/fresh2805-supplement-frozen/manifest.json, scripts/prepare_wuji_multigrasp_supplement.py。下一步：四组开发冻结后22旧+3补充新基础姿态各32扰动同GPU评估；补充新集结果单列。

多抓姿实查 2026-09-28T18:36:02.101374+00:00 dev-A-cp500-t5 running；远端PID 77555；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:36:02.101374+00:00 dev-A-cp500-t2 completed；远端PID 76883；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:36:34.478375+00:00 dev-C-cp500-t5 completed；远端PID 77245；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:36:34.478375+00:00 dev-C-cp750-t2 running；远端PID 77960；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:37:37.950732+00:00 dev-A-cp500-t5 completed；远端PID 77555；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:37:37.950732+00:00 dev-A-cp750-t2 running；远端PID 78259；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:38:41.343834+00:00 dev-C-cp750-t5 running；远端PID 78661；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:38:41.343834+00:00 dev-C-cp750-t2 completed；远端PID 77960；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:39:44.712381+00:00 dev-A-cp750-t5 running；远端PID 79063；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:39:44.712381+00:00 dev-A-cp750-t2 completed；远端PID 78259；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:40:17.206379+00:00 dev-C-cp750-t5 completed；远端PID 78661；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:40:17.206379+00:00 dev-C-cp1000-t2 running；远端PID 79331；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:41:20.554472+00:00 dev-A-cp750-t5 completed；远端PID 79063；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:41:20.554472+00:00 dev-A-cp1000-t2 running；远端PID 79679；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:42:24.914374+00:00 dev-C-cp1000-t2 completed；远端PID 79331；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:42:24.914374+00:00 dev-C-cp1000-t5 running；远端PID 80034；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:42:58.510626+00:00 dev-A-cp1000-t5 running；远端PID 80393；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:42:58.510626+00:00 dev-A-cp1000-t2 completed；远端PID 79679；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:44:02.541335+00:00 dev-C-cp1000-t5 completed；远端PID 80034；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:45:05.826486+00:00 dev-A-cp1000-t5 completed；远端PID 80393；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:53:53.650801+00:00 dev-B-cp250-t2 running；远端PID 83720；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:53:53.650801+00:00 mg_B_seed2801 completed；远端PID 3149；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T18:54:24.245682+00:00 B_full_budget_complete_AC_development_frozen

B训练18:53UTC正常完成1000轮，未触发4h超时；A/B/C最终CP均已CPU核验163840000交互。A/C全部八开发条件完成，按原规则均选CP750，严格2/5s等权开发分数A3.125%/C2.344%。这些是union16开发拟合结果，不是最终测试或多抓姿因素结论；B开发接续，D878继续。 证据：research/multigrasp-20260928/receipts/cp1000-ABC-1855.json, runs/multigrasp-20260928/development-A/frozen.json, runs/multigrasp-20260928/development-C/frozen.json。下一步：等待B/D开发冻结后开始25基础抓姿800回合统一测试；按最终证据选唯一诊断。

## 多抓姿 2026-09-28T18:54:29.552670+00:00 milestone_backup_verified

Backed up immutable B-1000 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/B-1000.json。下一步：Continue fixed1000epoch training and preregistered development selection。

多抓姿实查 2026-09-28T18:55:58.439376+00:00 dev-B-cp250-t2 completed；远端PID 83720；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:55:58.439376+00:00 dev-B-cp250-t5 running；远端PID 84320；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:57:32.672374+00:00 dev-B-cp250-t5 completed；远端PID 84320；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:57:32.672374+00:00 dev-B-cp500-t2 running；远端PID 84844；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:59:37.948370+00:00 dev-B-cp500-t2 completed；远端PID 84844；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T18:59:37.948370+00:00 dev-B-cp500-t5 running；远端PID 85583；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:01:12.370382+00:00 dev-B-cp500-t5 completed；远端PID 85583；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:01:12.370382+00:00 dev-B-cp750-t2 running；远端PID 86150；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:02:46.779378+00:00 dev-B-cp750-t2 completed；远端PID 86150；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:02:46.779378+00:00 dev-B-cp750-t5 running；远端PID 86709；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:04:52.073493+00:00 dev-B-cp1000-t2 running；远端PID 87319；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:04:52.073493+00:00 dev-B-cp750-t5 completed；远端PID 86709；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:06:26.429375+00:00 dev-B-cp1000-t2 completed；远端PID 87319；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:06:26.429375+00:00 dev-B-cp1000-t5 running；远端PID 87880；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:08:31.612678+00:00 dev-B-cp1000-t5 completed；远端PID 87880；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:15:05.248381+00:00 B_development_frozen_fourhour_utilization

B八条件开发全部严格0/128，按平局latest冻结CP1000；不得外推新测试或物理不可能。A/C分别CP750冻结，D958继续最后训练。整机最近4小时本方采样时加权79.60%，高于26%门槛/40%目标；非平台直接读数。 证据：runs/multigrasp-20260928/development-B/frozen.json, research/multigrasp-20260928/receipts/utilization-fourhour-1915.json。下一步：完成D开发后同GPU冻结评估；多抓姿如仍失败再选2-3单抓姿专家诊断。

多抓姿实查 2026-09-28T19:24:32.058374+00:00 dev-D-cp250-t2 completed；远端PID 93085；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:24:32.058374+00:00 dev-D-cp250-t5 running；远端PID 93152；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:24:32.058374+00:00 mg_D_seed2801 completed；远端PID 4716；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:24:57.714405+00:00 milestone_backup_verified

Backed up immutable D-1000 with identical remote/local SHA256; not evaluated or selected. 证据：/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/checkpoint-backups/D-1000.json。下一步：Continue fixed1000epoch training and preregistered development selection。

多抓姿实查 2026-09-28T19:25:05.282369+00:00 dev-D-cp250-t5 completed；远端PID 93152；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:25:05.282369+00:00 dev-D-cp500-t2 completed；远端PID 93419；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:25:08.397991+00:00 all_four_training_full_budget_complete

D19:24:06UTC终结，15217.42s墙钟；原PID退出+MAX EPOCHS NUM+最终CP共同确认完成，接管后exitcode不可得并已披露。四臂最终权重全部CPU核验1000轮/163840000交互、模型有限、优化器完整，全部16候选本地备份。D开发实际启动且首项完成，核心训练矩阵完整。 证据：research/multigrasp-20260928/receipts/cp1000-ABCD-1925.json, runs/multigrasp-20260928/mg_D_seed2801/status.json, research/multigrasp-20260928/receipts/checkpoint-backups/status.json。下一步：收齐D开发freeze即生成800最终初态并执行同预算主表/择优表。

多抓姿实查 2026-09-28T19:25:05.282369+00:00 dev-D-cp500-t5 running；远端PID 93569；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:25:38.579378+00:00 dev-D-cp750-t2 completed；远端PID 93844；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:25:38.579378+00:00 dev-D-cp500-t5 completed；远端PID 93569；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:25:38.579378+00:00 dev-D-cp750-t5 running；远端PID 93907；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:26:11.890836+00:00 dev-D-cp1000-t5 running；远端PID 94156；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:26:11.890836+00:00 dev-D-cp750-t5 completed；远端PID 93907；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:26:11.890836+00:00 dev-D-cp1000-t2 completed；远端PID 94093；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:26:45.259356+00:00 dev-D-cp1000-t5 completed；远端PID 94156；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:27:17.343102+00:00 final1000-v1-reference-static running；远端PID 94753；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:27:34.112847+00:00 all_models_and_final_cohort_frozen

四臂开发冻结A750/B1000/C750/D1000；D八条件均0strict/0alive。最终25基础×32=800初态在四模型冻结后生成，包含明确修订门禁的3补充新基础姿态，不按模型结果筛选。GPU0正式final1000-v1统一评估启动，先static后A/B/C/D/reference各fixed2/fixed5/arrival；所有模型主表均163840000训练交互。 证据：runs/multigrasp-20260928/development-D/frozen.json, research/multigrasp-20260928/data/final-cohort-v1/manifest.json, scripts/evaluate_wuji_multigrasp_frozen.py。下一步：核验final1000真实结果并运行development择优同批协议，独立复算后选唯一诊断。

## 多抓姿 2026-09-28T19:29:29.247286+00:00 selected_evaluation_queued_same_gpu

开发择优测试等待器远端PID95255实际启动，主表final1000-v1完整结束后GPU0顺序运行selected-v1，同800初态/协议；00:30UTC等待上限、执行2h上限均本轮截止前。主表正在实际静态基线，未按测试结果调整选择。 证据：scripts/continue_wuji_multigrasp_selected.py, research/multigrasp-20260928/data/final-cohort-v1/manifest.json。下一步：逐项收集真实冻结结果，独立复算并报告无效初态/静态失败分母。

多抓姿实查 2026-09-28T19:30:22.943374+00:00 final1000-v1-reference-static completed；远端PID 94753；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:30:22.943374+00:00 final1000-v1-A-fixed2 running；远端PID 95575；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:33:00.624988+00:00 final1000-v1-A-fixed2 completed；远端PID 95575；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:33:00.624988+00:00 final1000-v1-A-fixed5 running；远端PID 96163；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:36:09.823379+00:00 final1000-v1-A-fixed5 completed；远端PID 96163；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:36:09.823379+00:00 final1000-v1-A-arrival running；远端PID 96807；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:39:19.143364+00:00 final1000-v1-A-arrival completed；远端PID 96807；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:39:19.143364+00:00 final1000-v1-B-fixed2 running；远端PID 97451；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:41:57.165375+00:00 final1000-v1-B-fixed2 completed；远端PID 97451；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:41:57.165375+00:00 final1000-v1-B-fixed5 running；远端PID 98039；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:45:06.185490+00:00 final1000-v1-B-fixed5 completed；远端PID 98039；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:45:06.185490+00:00 final1000-v1-B-arrival running；远端PID 98727；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:47:53.497071+00:00 final_static_validity_measured

最终800初态静态687alive；补充新1/16/29各3/9/30存活、3/0/27严格刀身稳定，说明小扰动也可能破坏有效初始化。保留全部试验并单列静态有效/稳定子集分母，不筛选策略成功回合。首次离线hostpython无numpy，改既有环境后通过，无重复物理。 证据：research/multigrasp-20260928/receipts/final-static-validity.json。下一步：完成同预算主表与择优表，按基础抓姿和静态有效性分层独立复算。

多抓姿实查 2026-09-28T19:48:15.547376+00:00 final1000-v1-B-arrival completed；远端PID 98727；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:48:15.547376+00:00 final1000-v1-C-fixed2 running；远端PID 99372；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T19:50:05.792793+00:00 conditional_static_denominators_added

最终静态实测已有113不存活/144不满足稳定，因此分析表补充静态alive/stable子集的逐基础等权成功率、有效基础数和回合分母；全体结果同时保留，模型/阈值/测试初态不变。无静态有效回合的基础姿态标无分母而非0成功率。 证据：scripts/analyze_wuji_multigrasp_frozen.py, research/multigrasp-20260928/receipts/final-static-validity.json。下一步：完整主表后独立复算全体及条件分母并继续择优表。

多抓姿实查 2026-09-28T19:50:53.759373+00:00 final1000-v1-C-fixed2 completed；远端PID 99372；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:50:53.759373+00:00 final1000-v1-C-fixed5 running；远端PID 99959；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:53:31.943435+00:00 final1000-v1-C-fixed5 completed；远端PID 99959；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:53:31.943435+00:00 final1000-v1-C-arrival running；远端PID 100556；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:56:41.077483+00:00 final1000-v1-D-fixed2 running；远端PID 101188；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:56:41.077483+00:00 final1000-v1-C-arrival completed；远端PID 100556；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:59:19.126392+00:00 final1000-v1-D-fixed2 completed；远端PID 101188；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T19:59:19.126392+00:00 final1000-v1-D-fixed5 running；远端PID 101831；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:02:27.902373+00:00 final1000-v1-D-fixed5 completed；远端PID 101831；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:02:27.902373+00:00 final1000-v1-D-arrival running；远端PID 102420；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:05:05.909312+00:00 final1000-v1-reference-fixed2 running；远端PID 103062；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:05:05.909312+00:00 final1000-v1-D-arrival completed；远端PID 102420；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:08:19.738458+00:00 final1000-v1-reference-fixed2 completed；远端PID 103062；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:08:19.738458+00:00 final1000-v1-reference-fixed5 running；远端PID 103707；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:10:58.061188+00:00 final1000-v1-reference-fixed5 completed；远端PID 103707；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:10:58.061188+00:00 final1000-v1-reference-arrival running；远端PID 104250；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:12:03.502364+00:00 expert_row11_seed2810 running；远端PID 104800；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:12:03.502364+00:00 expert_row3_seed2810 running；远端PID 104797；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:12:03.502364+00:00 expert_row5_seed2810 running；远端PID 104799；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T20:12:15.552903+00:00 single_grasp_diagnostic_started

核心四组全部训练和三协议实际完成后，多抓姿B/D严格0；选择静态稳定32/32的3/5/11三源，分别代表无开合、操作失稳、可开合但端点不稳，唯一主要诊断分支为单抓姿专家。GPU1/2/3各1000轮、span.04、seed2810同随机初始化，奖励/物理不变，4h有界，预计23:30UTC完成并留评估交付。wrapper PID104599/104600/104601，真实trainPID须再核。 证据：research/multigrasp-20260928/expert-diagnostic-preregistration.json, scripts/train_wuji_multigrasp_expert.py。下一步：检查专家启动/吞吐，主表旧参考结束后独立分析，择优测试仍GPU0顺序进行。

多抓姿实查 2026-09-28T20:14:07.442457+00:00 final1000-v1-reference-arrival completed；远端PID 104250；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:14:41.902363+00:00 selected-v1-reference-static running；远端PID 105678；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:17:16.865501+00:00 selected-v1-A-fixed2 running；远端PID 106757；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:17:16.865501+00:00 selected-v1-reference-static completed；远端PID 105678；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T20:17:20.695596+00:00 A1000_representative_render_started

本地4090启动A1000视频重仿真，三格选择最终行70/96/352分别展示原成功/无操作/开合不稳。只作代表演示，重仿真批量和设备不同，最终视频实际结果需独立报告，不能当800env精确回放或新泛化统计。 证据：research/multigrasp-20260928/receipts/video-A1000-launch.json。下一步：检查视频真实结果/帧，主表独立复算已完成，择优评估和专家训练继续。

## 多抓姿 2026-09-28T20:18:02.821326+00:00 final1000_independent_analysis_complete

同预算16项物理评估全部完成并独立逐轨迹复算12000策略回合通过。严格fixed2 A9/B0/C19/D0/reference94(每800)，fixed5 A/B/C/D均0/reference93；全部新训练13基础、历史6基础、补充新3基础严格均0，静态稳定子集亦0。C收益仅原训练2s，未证明可靠独立收益。单seed，不泛化因果。专家3/5/11真实trainPID104797/104799/104800同初始化SHA0ad7813cc00ba3d935547e9f42bf0ca467f6683e47306317f3f400779716e94b；评估等待106197/106198/106199，源新扰动固定最终CP。 证据：research/multigrasp-20260928/final1000-analysis/report.json, scripts/evaluate_wuji_multigrasp_expert.py。下一步：完成择优评估、专家训练和冻结诊断，代表视频及GitHub权重交付。

多抓姿实查 2026-09-28T20:19:59.617539+00:00 selected-v1-A-fixed2 completed；远端PID 106757；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:19:59.617539+00:00 selected-v1-A-fixed5 running；远端PID 107419；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:23:09.377374+00:00 selected-v1-A-arrival running；远端PID 108072；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:23:09.377374+00:00 selected-v1-A-fixed5 completed；远端PID 107419；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T20:24:29.138607+00:00 weights_release_and_restore_verified

四个矩阵权重包共16CP已上传草稿Release398592814并服务端SHA核验；恢复入口对全部16权重逐一SHA检查并恢复epoch元数据和开发冻结记录。大原始trace继续上传。A1000代表视频600帧实检，实际0strict/2alive，已明确批量设备改变导致非精确回放。 证据：research/multigrasp-20260928/receipts/weight-restore-verification.txt, research/multigrasp-20260928/videos/A1000-three-grasps-manifest.json。下一步：完成择优表和专家诊断，最后发布Release并核验链接/所有权重哈希。

多抓姿实查 2026-09-28T20:26:22.039376+00:00 selected-v1-A-arrival completed；远端PID 108072；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:26:22.039376+00:00 selected-v1-B-fixed2 running；远端PID 108733；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T20:27:44.409719+00:00 selected_A750_original_base_render_started

开发选定A750固定2s正式800中26严格成功，前三个成功行64/65/66均来自同一原base2。启动本地视频三扰动，明确不是3独立抓姿，也不把重仿真当精确回放；A1000失败视频原样保留。 证据：research/multigrasp-20260928/receipts/video-A750-launch.json。下一步：核查实际视频是否严格成功；继续完整择优表/专家训练。

多抓姿实查 2026-09-28T20:29:03.385793+00:00 selected-v1-B-fixed2 completed；远端PID 108733；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:29:03.385793+00:00 selected-v1-B-fixed5 running；远端PID 109395；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T20:29:48.353767+00:00 A750_success_video_and_core_assets_verified

A750原base2三个扰动视频实际严格3/3、五完整周期、20s全程稳定，600帧抽检通过。明确单基础抓姿局部成功而非三抓姿泛化。四权重包及五主表trace包共9Release资产全部服务端SHA核验；旧参考权重和三个视频另行上传。主表图已按25基础抓姿绘出，宽松与严格分开。 证据：research/multigrasp-20260928/videos/A750-original-base2-three-perturbations-manifest.json, research/multigrasp-20260928/receipts/release-main-assets.json, research/multigrasp-20260928/final1000-analysis/per-base-outcomes.png。下一步：完成择优冻结结果与专家诊断；专家完成前不追加其它训练分支。

多抓姿实查 2026-09-28T20:32:19.547483+00:00 selected-v1-B-fixed5 completed；远端PID 109395；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:32:19.547483+00:00 selected-v1-B-arrival running；远端PID 110057；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:34:57.919377+00:00 selected-v1-B-arrival completed；远端PID 110057；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:34:57.919377+00:00 selected-v1-C-fixed2 running；远端PID 110719；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:38:07.219430+00:00 selected-v1-C-fixed2 completed；远端PID 110719；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:38:07.219430+00:00 selected-v1-C-fixed5 running；远端PID 111368；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:41:16.815383+00:00 selected-v1-C-arrival running；远端PID 112030；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:41:16.815383+00:00 selected-v1-C-fixed5 completed；远端PID 111368；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:44:00.542374+00:00 selected-v1-C-arrival completed；远端PID 112030；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:44:00.542374+00:00 selected-v1-D-fixed2 running；远端PID 112647；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:47:09.772374+00:00 selected-v1-D-fixed2 completed；远端PID 112647；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:47:09.772374+00:00 selected-v1-D-fixed5 running；远端PID 113309；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:49:47.813374+00:00 selected-v1-D-arrival running；远端PID 113961；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:49:47.813374+00:00 selected-v1-D-fixed5 completed；远端PID 113309；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:52:56.791501+00:00 selected-v1-reference-fixed2 running；远端PID 114578；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:52:56.791501+00:00 selected-v1-D-arrival completed；远端PID 113961；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:56:05.379380+00:00 selected-v1-reference-fixed2 completed；远端PID 114578；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:56:05.379380+00:00 selected-v1-reference-fixed5 running；远端PID 115240；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:58:43.773373+00:00 selected-v1-reference-fixed5 completed；远端PID 115240；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T20:58:43.773373+00:00 selected-v1-reference-arrival running；远端PID 115851；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T21:01:53.853777+00:00 selected-v1-reference-arrival completed；远端PID 115851；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

## 多抓姿 2026-09-28T21:04:57.801862+00:00 selected_frozen_independent_analysis_complete

择优16项完整、12000策略回合独立复算通过。fixed2 A75026/B10000/C75024/D10000(每800)，fixed5四组0；新增训练/历史/补充新抓姿均严格0，静态稳定子集相同。C同预算微收益未在择优表保留，无可靠动作范围额外收益证据。专家21:03UTC分别254/266/252轮，预计剩129-140min，继续既定唯一诊断。 证据：research/multigrasp-20260928/selected-analysis/report.json, research/multigrasp-20260928/receipts/experts-progress-2103.json。下一步：完成专家1000及独立源扰动评估；全部代码/权重/视频/报告最终发布。
