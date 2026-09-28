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
